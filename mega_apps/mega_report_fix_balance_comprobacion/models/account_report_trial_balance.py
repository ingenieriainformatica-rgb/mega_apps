# -*- coding: utf-8 -*-
import io
from collections import defaultdict

from odoo import models, fields, _  #type: ignore
from odoo.tools import SQL  #type: ignore
from odoo.tools.misc import xlsxwriter, format_date  #type: ignore


class MegaTrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    # -------------------------------------------------------------------------
    # Button injection
    # -------------------------------------------------------------------------

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XLSX Mega por tercero'),
            'sequence': 35,
            'action': 'export_file',
            'action_param': 'export_to_xlsx_mega_by_partner',
            'file_export_type': 'xlsx',
        })

    # -------------------------------------------------------------------------
    # Public export entry point
    # -------------------------------------------------------------------------

    def export_to_xlsx_mega_by_partner(self, options, response=None):
        report = self.env['account.report'].browse(options['report_id'])

        init_data, period_data = self._mega_query_trial_balance(report, options)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet('Balance de Comprobación')

        self._mega_write_xlsx(report, options, workbook, sheet, init_data, period_data)

        workbook.close()
        output.seek(0)

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        return {
            'file_name': f'balance_comprobacion_mega_{date_from}_{date_to}.xlsx',
            'file_content': output.read(),
            'file_type': 'xlsx',
        }

    # -------------------------------------------------------------------------
    # Data querying
    # -------------------------------------------------------------------------

    def _mega_query_trial_balance(self, report, options):
        """Return (init_data, period_data) as dicts {(account_id, partner_id): {debit, credit, balance}}."""
        options_by_col_group = report._split_options_per_column_group(options)

        init_col_key = None
        period_col_keys = []

        for col_key, col_group in options['column_groups'].items():
            forced = col_group.get('forced_options', {})
            if forced.get('no_impact_on_currency_table'):
                init_col_key = col_key
            elif forced.get('general_ledger_strict_range') and not forced.get('is_end_balance'):
                period_col_keys.append(col_key)

        # Initial balance
        init_data = {}
        if init_col_key:
            init_opts = options_by_col_group[init_col_key]
            init_data = self._mega_sql_grouped(report, init_opts, 'from_beginning')

        # Period movements
        period_data = {}
        for col_key in period_col_keys:
            chunk = self._mega_sql_grouped(report, options_by_col_group[col_key], 'strict_range')
            for key, vals in chunk.items():
                if key in period_data:
                    period_data[key]['debit'] += vals['debit']
                    period_data[key]['credit'] += vals['credit']
                    period_data[key]['balance'] += vals['balance']
                else:
                    period_data[key] = dict(vals)

        return init_data, period_data

    def _mega_sql_grouped(self, report, options, date_scope):
        """Run a SQL query grouped by (account_id, partner_id)."""
        extra_domain = []

        if date_scope == 'from_beginning':
            date_from = fields.Date.from_string(options['date']['date_from'])
            fy_dates = self.env.company.compute_fiscalyear_dates(date_from)
            extra_domain = [
                '|',
                ('date', '>=', fields.Date.to_string(fy_dates['date_from'])),
                ('account_id.include_initial_balance', '=', True),
            ]
            if options.get('include_current_year_in_unaff_earnings'):
                extra_domain += [('account_id.include_initial_balance', '=', True)]

        query = report._get_report_query(options, date_scope, domain=extra_domain)

        sql = SQL(
            """
            SELECT
                account_move_line.account_id  AS account_id,
                account_move_line.partner_id  AS partner_id,
                SUM(%(debit)s)                AS debit,
                SUM(%(credit)s)               AS credit,
                SUM(%(balance)s)              AS balance
            FROM %(table_refs)s
            %(currency_join)s
            WHERE %(where)s
            GROUP BY account_move_line.account_id, account_move_line.partner_id
            """,
            debit=report._currency_table_apply_rate(SQL("account_move_line.debit")),
            credit=report._currency_table_apply_rate(SQL("account_move_line.credit")),
            balance=report._currency_table_apply_rate(SQL("account_move_line.balance")),
            currency_join=report._currency_table_aml_join(options),
            table_refs=query.from_clause,
            where=query.where_clause,
        )

        result = {}
        for row in self.env.execute_query_dict(sql):
            key = (row['account_id'], row['partner_id'])
            result[key] = {
                'debit': float(row['debit'] or 0.0),
                'credit': float(row['credit'] or 0.0),
                'balance': float(row['balance'] or 0.0),
            }
        return result

    # -------------------------------------------------------------------------
    # XLSX writer
    # -------------------------------------------------------------------------

    # Column indices (0-based)
    _COL_EMPTY = 0   # A – margen vacío
    _COL_CODE = 1    # B – CODIGO
    _COL_NAME = 2    # C – NOMBRE CUENTA
    _COL_DTYPE = 3   # D – Tipo doc
    _COL_DOC = 4     # E – Documento
    _COL_DV = 5      # F – dv
    _COL_INIT = 6    # G – SALDO INICIAL
    _COL_DEBIT = 7   # H – DEBITOS
    _COL_CREDIT = 8  # I – CREDITOS
    _COL_FINAL = 9   # J – SALDO FINAL
    _LAST_COL = 9

    def _mega_write_xlsx(self, report, options, workbook, sheet, init_data, period_data):
        company = self.env.company

        # ---- Colours -------------------------------------------------------
        BLUE_TITLE = '#1F3864'   # dark navy – encabezado empresa
        BLUE_GROUP = '#1F3864'   # dark navy – grupos de cuenta
        BLUE_HDR_BG = '#1F497D'  # header background

        # ---- Number format -------------------------------------------------
        NUM_FMT = '$ #,##0.00'

        # ---- Formats -------------------------------------------------------
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 13, 'font_color': BLUE_TITLE,
            'valign': 'vcenter', 'align': 'left',
        })
        info_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'font_color': BLUE_TITLE,
            'valign': 'vcenter', 'align': 'left',
        })
        gen_time_fmt = workbook.add_format({
            'font_size': 9, 'font_color': '#555555',
            'valign': 'vcenter', 'align': 'left', 'italic': True,
        })
        header_fmt = workbook.add_format({
            'bold': True, 'font_color': 'white', 'bg_color': BLUE_HDR_BG,
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
        })
        group_txt_fmt = workbook.add_format({'bold': True, 'font_color': BLUE_GROUP})
        group_num_fmt = workbook.add_format({'bold': True, 'font_color': BLUE_GROUP, 'num_format': NUM_FMT})
        account_txt_fmt = workbook.add_format({'bold': True})
        account_num_fmt = workbook.add_format({'bold': True, 'num_format': NUM_FMT})
        partner_txt_fmt = workbook.add_format({'indent': 1})
        partner_num_fmt = workbook.add_format({'indent': 1, 'num_format': NUM_FMT})
        total_txt_fmt = workbook.add_format({'bold': True, 'top': 2})
        total_num_fmt = workbook.add_format({'bold': True, 'top': 2, 'num_format': NUM_FMT})

        # ---- Column widths -------------------------------------------------
        sheet.set_column(self._COL_EMPTY,  self._COL_EMPTY,  3)
        sheet.set_column(self._COL_CODE,   self._COL_CODE,   14)
        sheet.set_column(self._COL_NAME,   self._COL_NAME,   44)
        sheet.set_column(self._COL_DTYPE,  self._COL_DTYPE,  14)
        sheet.set_column(self._COL_DOC,    self._COL_DOC,    16)
        sheet.set_column(self._COL_DV,     self._COL_DV,     5)
        sheet.set_column(self._COL_INIT,   self._COL_INIT,   18)
        sheet.set_column(self._COL_DEBIT,  self._COL_DEBIT,  18)
        sheet.set_column(self._COL_CREDIT, self._COL_CREDIT, 18)
        sheet.set_column(self._COL_FINAL,  self._COL_FINAL,  18)

        # ---- Build company NIT display (with dash before DV) ---------------
        nit_raw = company.vat or ''
        nit_num, nit_dv = self._mega_nit_split(nit_raw)
        nit_display = f'NIT {nit_num}-{nit_dv}' if nit_dv else f'NIT {nit_raw}'

        date_from_str = format_date(self.env, options['date']['date_from'])
        date_to_str = format_date(self.env, options['date']['date_to'])

        # Hora de generación en zona horaria del usuario
        gen_dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        gen_time_str = gen_dt.strftime('Generado el %d/%m/%Y a las %H:%M')

        # ---- Header rows (1–6 en índice 0 = filas 2–7 en spreadsheet) ------
        #   Row 0  → separador vacío pequeño (3px)
        #   Row 1  → nombre empresa         (22px)  merge B:J
        #   Row 2  → NIT                    (18px)  merge B:J
        #   Row 3  → período                (18px)  merge B:J
        #   Row 4  → hora de generación     (14px)  merge B:J
        #   Row 5  → separador vacío pequeño (3px)
        #   Row 6  → encabezados de columna (30px)
        HEADER_ROW = 6   # 0-based = fila 7 en spreadsheet

        sheet.set_row(0, 3)
        sheet.set_row(1, 22)
        sheet.set_row(2, 18)
        sheet.set_row(3, 18)
        sheet.set_row(4, 14)
        sheet.set_row(5, 3)
        sheet.set_row(HEADER_ROW, 30)

        # Encabezado con merge_range B:J para evitar desbordamiento de texto
        sheet.merge_range(1, self._COL_CODE, 1, self._LAST_COL, company.name or '', title_fmt)
        sheet.merge_range(2, self._COL_CODE, 2, self._LAST_COL, nit_display, info_fmt)
        sheet.merge_range(3, self._COL_CODE, 3, self._LAST_COL,
                          f'Fecha: {date_from_str} - {date_to_str}',
                          info_fmt)
        sheet.merge_range(4, self._COL_CODE, 4, self._LAST_COL, gen_time_str, gen_time_fmt)

        # ---- Column headers (row 7, 0-based = fila 8 en spreadsheet) ------
        col_labels = {
            self._COL_EMPTY:  '',
            self._COL_CODE:   'CODIGO',
            self._COL_NAME:   'NOMBRE CUENTA',
            self._COL_DTYPE:  'Tipo documento /\ncédula',
            self._COL_DOC:    'Documento',
            self._COL_DV:     'dv',
            self._COL_INIT:   'SALDO INICIAL',
            self._COL_DEBIT:  'DEBITOS',
            self._COL_CREDIT: 'CREDITOS',
            self._COL_FINAL:  'SALDO FINAL',
        }
        for col, label in col_labels.items():
            sheet.write(HEADER_ROW, col, label, header_fmt)

        sheet.freeze_panes(HEADER_ROW + 1, 0)
        sheet.autofilter(HEADER_ROW, self._COL_CODE, HEADER_ROW, self._LAST_COL)

        # ---- Reorganise data by account_id ---------------------------------
        by_account = defaultdict(lambda: {'init': {}, 'period': {}})
        all_partner_ids = set()

        for (acc_id, pid), vals in init_data.items():
            by_account[acc_id]['init'][pid] = vals
            if pid:
                all_partner_ids.add(pid)

        for (acc_id, pid), vals in period_data.items():
            by_account[acc_id]['period'][pid] = vals
            if pid:
                all_partner_ids.add(pid)

        if not by_account:
            return

        # ---- Fetch accounts ------------------------------------------------
        accounts = self.env['account.account'].search(
            [('id', 'in', list(by_account.keys()))]
        )

        # ---- Fetch partners ------------------------------------------------
        partners = self.env['res.partner'].with_context(active_test=False).search(
            [('id', 'in', list(all_partner_ids))]
        )
        partner_map = {p.id: p for p in partners}

        # ---- Compute individual account totals -----------------------------
        account_totals = {}
        for account in accounts:
            acc_data = by_account[account.id]
            acc_init = sum(v['balance'] for v in acc_data['init'].values())
            acc_debit = sum(v['debit'] for v in acc_data['period'].values())
            acc_credit = sum(v['credit'] for v in acc_data['period'].values())
            account_totals[account.code] = {
                'name': account.name,
                'account': account,
                'init': acc_init,
                'debit': acc_debit,
                'credit': acc_credit,
                'final': acc_init + acc_debit - acc_credit,
            }

        # ---- Load account.group map ----------------------------------------
        # group_map: {code_prefix_start: (name, code_prefix_end)}
        all_groups = self.env['account.group'].search([])
        group_map = {}
        for g in all_groups:
            if g.code_prefix_start and g.code_prefix_start not in group_map:
                group_map[g.code_prefix_start] = (g.name, g.code_prefix_end or g.code_prefix_start)

        # ---- Determine which groups are parents of the queried accounts ----
        # A group is a parent of an account if the account code's prefix matches the group range
        parent_group_prefixes = {}  # prefix → name
        for acc_code in account_totals.keys():
            for prefix, (gname, prefix_end) in group_map.items():
                if len(prefix) < len(acc_code):
                    truncated = acc_code[:len(prefix)]
                    if prefix <= truncated <= prefix_end:
                        parent_group_prefixes[prefix] = gname

        # ---- Compute group totals (sum of all child accounts) --------------
        group_totals = {}
        for prefix, gname in parent_group_prefixes.items():
            plen = len(prefix)
            g_init = g_debit = g_credit = 0.0
            for acc_code, totals in account_totals.items():
                truncated = acc_code[:plen]
                prefix_end = group_map[prefix][1]
                if prefix <= truncated <= prefix_end:
                    g_init += totals['init']
                    g_debit += totals['debit']
                    g_credit += totals['credit']
            group_totals[prefix] = {
                'name': gname,
                'init': g_init,
                'debit': g_debit,
                'credit': g_credit,
                'final': g_init + g_debit - g_credit,
            }

        # ---- Build unified sorted list of entries --------------------------
        # Sort key: (code, is_account) → groups before accounts with same prefix
        all_entries = []
        for prefix, data in group_totals.items():
            all_entries.append((prefix, False, data))
        for acc_code, data in account_totals.items():
            all_entries.append((acc_code, True, data))

        all_entries.sort(key=lambda x: (x[0], x[1]))

        # ---- Write data rows -----------------------------------------------
        row = HEADER_ROW + 1
        grand_init = grand_debit = grand_credit = grand_final = 0.0

        for code, is_account, entry in all_entries:

            if not is_account:
                # ---- Group row (bold, dark blue) ---------------------------
                self._mega_write_row(
                    sheet, row,
                    txt_fmt=group_txt_fmt, num_fmt=group_num_fmt,
                    code=code, name=entry['name'],
                    dtype='', doc='', dv='',
                    init=entry['init'], debit=entry['debit'],
                    credit=entry['credit'], final=entry['final'],
                )
                row += 1

            else:
                # ---- Account header row (bold black) -----------------------
                self._mega_write_row(
                    sheet, row,
                    txt_fmt=account_txt_fmt, num_fmt=account_num_fmt,
                    code=code, name=entry['name'],
                    dtype='', doc='', dv='',
                    init=entry['init'], debit=entry['debit'],
                    credit=entry['credit'], final=entry['final'],
                )
                row += 1

                # ---- Partner detail rows -----------------------------------
                account = entry['account']
                acc_data = by_account[account.id]
                init_by_pid = acc_data['init']
                period_by_pid = acc_data['period']
                all_pids = set(init_by_pid.keys()) | set(period_by_pid.keys())

                sorted_pids = sorted(
                    all_pids,
                    key=lambda pid: (
                        partner_map[pid].name.upper()
                        if pid and partner_map.get(pid) and partner_map[pid].name
                        else ('ZZZZZZ' if pid else 'ZZZZZZZ')
                    ),
                )

                for pid in sorted_pids:
                    p_init = init_by_pid.get(pid, {'balance': 0.0})
                    p_period = period_by_pid.get(pid, {'debit': 0.0, 'credit': 0.0})
                    p_init_bal = p_init['balance']
                    p_debit = p_period['debit']
                    p_credit = p_period['credit']
                    p_final = p_init_bal + p_debit - p_credit

                    partner = partner_map.get(pid) if pid else None
                    if partner:
                        p_name = partner.name or ''
                        doc_type, doc_number, dv = self._mega_partner_doc_info(partner)
                    else:
                        p_name = _('Sin tercero')
                        doc_type = doc_number = dv = ''

                    # Partner row: repeat account code in column B
                    self._mega_write_row(
                        sheet, row,
                        txt_fmt=partner_txt_fmt, num_fmt=partner_num_fmt,
                        code=code, name=p_name,
                        dtype=doc_type, doc=doc_number, dv=dv,
                        init=p_init_bal, debit=p_debit,
                        credit=p_credit, final=p_final,
                    )
                    row += 1

                grand_init += entry['init']
                grand_debit += entry['debit']
                grand_credit += entry['credit']
                grand_final += entry['final']

        # ---- Grand total row -----------------------------------------------
        self._mega_write_row(
            sheet, row,
            txt_fmt=total_txt_fmt, num_fmt=total_num_fmt,
            code='', name='TOTALES',
            dtype='', doc='', dv='',
            init=grand_init, debit=grand_debit,
            credit=grand_credit, final=grand_final,
        )

    def _mega_write_row(self, sheet, row,
                        txt_fmt, num_fmt,
                        code, name, dtype, doc, dv,
                        init, debit, credit, final):
        """Write a single XLSX data row using the provided formats."""
        sheet.write(row, self._COL_EMPTY,  '',     txt_fmt)
        sheet.write(row, self._COL_CODE,   code,   txt_fmt)
        sheet.write(row, self._COL_NAME,   name,   txt_fmt)
        sheet.write(row, self._COL_DTYPE,  dtype,  txt_fmt)
        sheet.write(row, self._COL_DOC,    doc,    txt_fmt)
        sheet.write(row, self._COL_DV,     dv,     txt_fmt)
        sheet.write(row, self._COL_INIT,   init,   num_fmt)
        sheet.write(row, self._COL_DEBIT,  debit,  num_fmt)
        sheet.write(row, self._COL_CREDIT, credit, num_fmt)
        sheet.write(row, self._COL_FINAL,  final,  num_fmt)

    # -------------------------------------------------------------------------
    # Partner document helpers
    # -------------------------------------------------------------------------

    def _mega_partner_doc_info(self, partner):
        """Return (doc_type_label, doc_number, dv) for display in the XLSX."""
        vat = (partner.vat or '').strip()

        id_type = getattr(partner, 'l10n_latam_identification_type_id', False)
        doc_code = ''
        if id_type:
            doc_code = getattr(id_type, 'l10n_co_document_code', '') or ''

        if doc_code == 'rut' or (partner.is_company and not doc_code and vat):
            nit, dv = self._mega_nit_split(vat)
            return ('NIT', nit, dv)

        doc_type_map = {
            'national_citizen_id': 'CC',
            'id_document': 'CC',
            'civil_registration': 'RC',
            'id_card': 'TI',
            'foreign_colombian_card': 'CE',
            'foreign_resident_card': 'CR',
            'passport': 'PAS',
            'foreign_id_card': 'IE',
            'PEP': 'PEP',
            'PPT': 'PPT',
            'niup_id': 'NIUP',
        }

        if doc_code in doc_type_map:
            label = doc_type_map[doc_code]
        elif id_type and getattr(id_type, 'name', ''):
            label = (id_type.name or '')[:6].upper()  #type: ignore
        elif partner.is_company:
            label = 'NIT'
        else:
            label = 'CC'

        return (label, vat, '')

    def _mega_nit_split(self, vat_raw):
        """
        Extract (nit_digits, check_digit) from a raw NIT/VAT string.
        Handles: '900325964-5', '9003259645', '900325964'.
        Falls back to computing DV via DIAN algorithm.
        """
        if not vat_raw:
            return ('', '')

        vat = str(vat_raw).strip()

        # Format 'XXXXXXXXX-Y'
        if '-' in vat:
            parts = vat.rsplit('-', 1)
            nit_part = ''.join(c for c in parts[0] if c.isdigit())
            dv_part = parts[1].strip()
            if dv_part.isdigit() and len(dv_part) == 1:
                return (nit_part, dv_part)

        digits = ''.join(c for c in vat if c.isdigit())
        if not digits:
            return (vat, '')

        # 10+ digits: last digit is DV
        if len(digits) >= 10:
            return (digits[:-1], digits[-1])

        # Compute DV via DIAN algorithm
        weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        total = sum(int(d) * w for d, w in zip(reversed(digits), weights))
        remainder = total % 11
        dv = str(remainder) if remainder in (0, 1) else str(11 - remainder)
        return (digits, dv)
