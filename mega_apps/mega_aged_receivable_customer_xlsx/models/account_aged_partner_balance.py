from odoo import models

MEGA_CUSTOM_LABELS = ('partner_name', 'partner_vat', 'document_date')


class AgedPartnerBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.aged.partner.balance.report.handler'

    def _aged_partner_report_custom_engine_common(self, options, internal_type, current_groupby, next_groupby, offset=0, limit=None):
        # Overridden here (the method shared by both Aged Receivable and Aged Payable) rather than
        # on '_report_custom_engine_aged_receivable': when a line is fully unfolded (as happens for
        # every XLSX/PDF export), account_reports resolves its detail rows through
        # '_common_custom_unfold_all_batch_data_generator', which calls this common method directly
        # and skips '_report_custom_engine_aged_receivable' entirely. Enriching here covers both paths.
        # Harmless for Aged Payable: it gets the extra keys too, but never exposes them since no
        # column/expression references them there.
        result = super()._aged_partner_report_custom_engine_common(
            options, internal_type, current_groupby, next_groupby, offset=offset, limit=limit,
        )
        return self._mega_add_customer_info(result, current_groupby)

    def _mega_add_customer_info(self, result, current_groupby):
        """ Enrich the id-level dicts (one per journal item) with 'partner_name'/'partner_vat'/
        'document_date' keys.

        'partner_name'/'partner_vat' deliberately read from account.move.line.move_id.partner_id
        (the document's own customer, i.e. exactly what the invoice/credit note/payment form shows)
        rather than from account.move.line.partner_id directly. The two are normally the same, but
        can diverge on real data (e.g. a journal item whose partner_id was changed independently of
        its invoice, or a manual collection/payment entry) - and account_move_line.partner_id is
        also what the standard report itself groups and labels by, so these columns must not just
        mirror that same, potentially stale, value: they must reflect the actual document owner.

        'document_date' reads account.move.line.date (the accounting date every journal item has),
        unlike the standard 'invoice_date' column/expression which stays blank for anything that
        isn't an invoice line (manual payments, misc entries, ...).
        """
        if current_groupby != 'id':
            # Partner-level (or ungrouped/root) rows never carry an invoice of their own; the group
            # heading already shows the customer name, so these columns stay blank here (see also
            # _prepare_partner_values for the unfold-all batch path's version of this same row).
            entries = [entry for _key, entry in result] if isinstance(result, list) else [result]
            for entry in entries:
                entry['partner_name'] = ''
                entry['partner_vat'] = ''
                entry['document_date'] = None
            return result

        aml_id_and_entry = list(result)
        move_lines = self.env['account.move.line'].browse([aml_id for aml_id, _entry in aml_id_and_entry])
        # No sudo(): account.move.line/res.partner access rules and company visibility apply as usual.
        # One batched prefetch for the whole page of rows, not a query per line.
        info_by_aml = {
            move_line.id: (
                move_line.move_id.partner_id.commercial_partner_id.name or '',
                move_line.move_id.partner_id.commercial_partner_id.vat or '',
                move_line.date,
            )
            for move_line in move_lines
        }
        for aml_id, entry in aml_id_and_entry:
            name, vat, document_date = info_by_aml.get(aml_id, ('', '', None))
            entry['partner_name'] = name
            entry['partner_vat'] = vat
            entry['document_date'] = document_date

        return result

    def _prepare_partner_values(self):
        # Used by the unfold-all batch path (see above) to build the partner-level aggregate row;
        # needs the same defaults too, since our expressions are evaluated against it the same way
        # as any other. The partner group row itself stays blank either way (see data file).
        values = super()._prepare_partner_values()
        values['partner_name'] = ''
        values['partner_vat'] = ''
        values['document_date'] = None
        return values


class AgedReceivableCustomHandler(models.AbstractModel):
    _inherit = 'account.aged.receivable.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # These columns are declared on the report (see data/aged_receivable_customer_column.xml) so
        # they always come back from the standard column-building step, but they must only show up
        # for the dedicated "XLSX con Cliente y NIT por fila" cog-menu action
        # (models/account_report.py), never on the interactive table, the PDF export, or the
        # standard XLSX button.
        # Read from env.context, not from `previous_options`: options are echoed back and reused by
        # the report's on-screen state across later, unrelated requests, so a flag stored there would
        # leak (this is exactly what happened before this file was fixed - the column stayed visible
        # on screen after a single export request).
        if not report.env.context.get('mega_show_partner_name_column'):
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] not in MEGA_CUSTOM_LABELS
            ]
