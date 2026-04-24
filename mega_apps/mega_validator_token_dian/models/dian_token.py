# -*- coding: utf-8 -*-
import io
import base64
import re
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from httplib2 import FailedToDecompressContent

import xlsxwriter  # type: ignore

from odoo import fields, models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


class MegaDianToken(models.Model):
    _name = "mega.dian.token"
    _description = "Token DIAN"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Nombre del token",
        required=True,
        tracking=True,
    )

    date_start = fields.Date(
        string="Fecha inicial",
        required=True,
        tracking=True,
    )

    date_end = fields.Date(
        string="Fecha final",
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("loaded", "Con archivos"),
            ("processed", "Procesado"),
            ("validated", "Validado"),
            ("error", "Error"),
        ],
        string="Estado",
        default="draft",
        tracking=True,
    )

    note = fields.Text(string="Observaciones")

    file_ids = fields.One2many(
        "mega.dian.token.file",
        "token_id",
        string="Archivos / registros",
    )

    file_count = fields.Integer(
        string="Cantidad de registros",
        compute="_compute_file_count",
        store=False,
    )

    def _compute_file_count(self):
        for rec in self:
            rec.file_count = len(rec.file_ids)

    def action_open_upload_wizard(self):
        self.ensure_one()
        if not self.id:
            raise UserError(_("Primero debes guardar el token DIAN antes de subir archivos."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Subir archivo DIAN"),
            "res_model": "mega.dian.token.upload.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_token_id": self.id,
            },
        }

    # ============================================================
    # PROCESAMIENTO / CONCILIACIÓN
    # ============================================================
    def action_process_token(self):
        self.ensure_one()

        if not self.file_ids:
            raise UserError(_("No existen registros para procesar en este token DIAN."))

        move_model = self.env["account.move"].sudo()
        partner_model = self.env["res.partner"].sudo()

        all_reconciled = True

        for line in self.file_ids:

            is_reconciled = self._process_single_token_line(
                line=line,
                move_model=move_model,
                partner_model=partner_model,
            )
            if not is_reconciled:
                all_reconciled = False

        if all_reconciled and self.file_ids:
            self.state = "processed"

    def _process_single_token_line(self, line, move_model, partner_model):
        nit_emisor = self._normalize_text(line.nit_emisor)
        prefijo = self._normalize_text(line.prefijo)
        folio = self._normalize_text(line.folio)

        line_total = self._to_amount(line.total)
        line_iva = self._to_amount(line.iva)

        partner = self._find_partner_by_vat(partner_model, nit_emisor)

        ref_candidates = self._build_reference_candidates(prefijo=prefijo, folio=folio)
        candidate_moves = self._find_candidate_moves(move_model=move_model, partner=partner)

        if not candidate_moves:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_("No se encontraron facturas proveedor para el NIT identificado."),
                is_reconciled=False,
            )
            return FailedToDecompressContent

        # 1) Coincidencia por referencia
        reference_matches = candidate_moves.filtered(
            lambda m: self._match_reference(m, ref_candidates)
        )

        if not reference_matches:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_("No se encontró factura en Odoo con referencia coincidente."),
                is_reconciled=False,
            )
            return False

        # 2) Coincidencia exacta: referencia + IVA + total
        exact_matches = reference_matches.filtered(
            lambda m: self._amounts_equal(self._get_move_dian_iva(m), line_iva)
            and self._amounts_equal(self._get_move_dian_total(m), line_total)
        )

        if len(exact_matches) == 1:
            self._write_line_match(
                line=line,
                move=exact_matches[0],
                status="matched",
                note=_("Coincidencia exacta por NIT, referencia, IVA y total."),
                is_reconciled=True,
            )
            return True

        if len(exact_matches) > 1:
            self._write_line_result(
                line=line,
                status="multiple",
                note=_("Se encontraron múltiples facturas con coincidencia exacta."),
                is_reconciled=False,
            )
            return False

        # 3) Coincidencia parcial por referencia + IVA
        partial_by_iva = reference_matches.filtered(
            lambda m: self._amounts_equal(self._get_move_dian_iva(m), line_iva)
        )

        if len(partial_by_iva) == 1:
            self._write_line_match(
                line=line,
                move=partial_by_iva[0],
                status="partial",
                note=_("Coincide NIT, referencia e IVA, pero no el total."),
                is_reconciled=False,
            )
            return False

        if len(partial_by_iva) > 1:
            self._write_line_result(
                line=line,
                status="multiple",
                note=_("Se encontraron múltiples coincidencias por referencia e IVA."),
                is_reconciled=False,
            )
            return False

        # 4) Coincidencia parcial por referencia + total
        partial_by_total = reference_matches.filtered(
            lambda m: self._amounts_equal(self._get_move_dian_total(m), line_total)
        )

        if len(partial_by_total) == 1:
            self._write_line_match(
                line=line,
                move=partial_by_total[0],
                status="partial",
                note=_("Coincide NIT, referencia y total, pero no el IVA."),
                is_reconciled=False,
            )
            return False

        if len(partial_by_total) > 1:
            self._write_line_result(
                line=line,
                status="multiple",
                note=_("Se encontraron múltiples coincidencias por referencia y total."),
                is_reconciled=False,
            )
            return False

        # 5) Si encontró referencia, pero no montos, dejar parcial
        move = reference_matches[:1]
        if move:
            self._write_line_match(
                line=line,
                move=move,
                status="partial",
                note=_("La referencia coincide, pero los valores de IVA y total no coinciden exactamente."),
                is_reconciled=False,
            )
            return False

        self._write_line_result(
            line=line,
            status="not_found",
            note=_("No se encontró factura en Odoo con coincidencia suficiente."),
            is_reconciled=False,
        )
        return False

    def _find_partner_by_vat(self, partner_model, vat):
        if not vat:
            return partner_model.browse()
        return partner_model.search([("vat", "ilike", vat)], limit=1)

    def _find_candidate_moves(self, move_model, partner):
        domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "in", ["draft", "posted"]),
            ("invoice_date", ">=", self.date_start),
            ("invoice_date", "<=", self.date_end),
        ]
        if partner:
            domain.append(("partner_id", "=", partner.id))
        return move_model.search(domain)

    def _extract_letters(self, value):
        return re.sub(r"[^A-Z]", "", self._sanitize_reference(value))

    def _extract_digits(self, value):
        return re.sub(r"\D", "", str(value or ""))

    def _build_reference_candidates(self, prefijo, folio):
        """
        Construye candidatos de referencia y además devuelve
        componentes útiles para comparación flexible.
        """
        prefijo = self._normalize_text(prefijo)
        folio = self._normalize_text(folio)

        candidates = []

        if prefijo and folio:
            candidates.extend([
                f"{prefijo}{folio}",
                f"{prefijo}-{folio}",
                f"{prefijo} {folio}",
                f"{prefijo}/{folio}",
            ])

        if folio:
            candidates.append(folio)

        return list(dict.fromkeys(candidates))

    def _write_line_match(self, line, move, status, note, is_reconciled):
        self._write_line_result(
            line=line,
            status=status,
            note=note,
            is_reconciled=is_reconciled,
            extra_vals={
                "partner_id": move.partner_id.id,
                "move_id": move.id,
                "odoo_ref": move.ref or move.name,
                "fecha_factura_odoo": move.invoice_date,
                "odoo_total": self._get_move_dian_total(move),
                "odoo_iva": self._get_move_dian_iva(move),
            },
        )

    def _write_line_result(self, line, status, note, is_reconciled, extra_vals=None):
        vals = {
            "validation_status": status,
            "validation_note": note,
            "is_reconciled": is_reconciled,
        }
        if extra_vals:
            vals.update(extra_vals)
        line.write(vals)

    def _normalize_text(self, value):
        return str(value or "").strip()

    def _to_amount(self, value):
        return float(value or 0.0)

    def _amounts_equal(self, left, right, precision="0.01"):
        """
        Compara montos con redondeo decimal a 2 posiciones.
        """
        left_dec = Decimal(str(left or 0.0)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)
        right_dec = Decimal(str(right or 0.0)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)
        return left_dec == right_dec

    def _sanitize_reference(self, value):
        return (
            str(value or "")
            .strip()
            .replace("-", "")
            .replace(" ", "")
            .replace("/", "")
            .upper()
        )

    def _match_reference(self, move, ref_candidates, prefijo=None, folio=None):
        move_ref = self._sanitize_reference(move.ref)
        move_name = self._sanitize_reference(move.name)

        move_ref_digits = self._extract_digits(move.ref)
        move_name_digits = self._extract_digits(move.name)

        normalized_candidates = [self._sanitize_reference(ref) for ref in ref_candidates if ref]
        candidate_digits = [self._extract_digits(ref) for ref in ref_candidates if ref]

        folio_digits = self._extract_digits(folio)

        # 1. Coincidencia exacta normalizada
        if move_ref in normalized_candidates or move_name in normalized_candidates:
            return True

        # 2. Coincidencia exacta por solo números
        if move_ref_digits and move_ref_digits in candidate_digits:
            return True

        if move_name_digits and move_name_digits in candidate_digits:
            return True

        # 3. Coincidencia por folio numérico al final
        if folio_digits:
            if move_ref_digits.endswith(folio_digits):
                return True
            if move_name_digits.endswith(folio_digits):
                return True

        return False

    def _get_move_dian_iva(self, move):
        """
        Retorna solo el IVA positivo del documento.
        Excluye retenciones y otros impuestos negativos.
        """
        iva_amount = 0.0

        for line in move.line_ids.filtered(lambda l: l.tax_line_id):
            tax_name = (line.tax_line_id.name or "").lower()
            amount = line.amount_currency if line.currency_id else line.balance

            if "iva" in tax_name and (amount or 0.0) > 0:
                iva_amount += abs(amount or 0.0)

        return iva_amount

    def _get_move_dian_total(self, move):
        """
        Total DIAN bruto = base + IVA positivo.
        No descuenta retenciones.
        """
        untaxed = move.amount_untaxed or 0.0
        iva_amount = self._get_move_dian_iva(move)
        return untaxed + iva_amount

    # ============================================================
    # EXPORTACIÓN EXCEL
    # ============================================================
    # ============================================================
    # EXPORTACIÓN EXCEL
    # ============================================================
    def action_export_excel(self):
        """
        Exporta los registros del token DIAN a Excel con:
        - columnas DIAN
        - columnas Odoo
        - fechas DIAN y Odoo
        - estado de conciliación
        - diferencias de IVA, total y fecha
        - resaltado visual cuando existan diferencias
        """
        self.ensure_one()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Token DIAN")

        formats = self._get_excel_formats(workbook)
        headers = self._get_excel_headers()
        widths = self._get_excel_column_widths()

        # Encabezados
        for col, (title, fmt_key) in enumerate(headers):
            sheet.write(0, col, title, formats[fmt_key])

        # Anchos
        for col, width in widths.items():
            sheet.set_column(col, col, width)

        # Extras visuales
        sheet.set_row(0, 24)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, 0, len(headers) - 1)

        # Datos
        row = 1
        for line in self.file_ids:
            self._write_excel_line(sheet=sheet, row=row, line=line, formats=formats)
            row += 1

        workbook.close()
        output.seek(0)

        attachment = self.env["ir.attachment"].create({
            "name": f"Token_DIAN_{self.name}.xlsx",
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


    def _get_excel_formats(self, workbook):
        return {
            "header_dian": workbook.add_format({
                "bold": True,
                "bg_color": "#66CC18",
                "font_color": "#000000",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }),
            "header_odoo": workbook.add_format({
                "bold": True,
                "bg_color": "#8360ED",
                "font_color": "#FFFFFF",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }),
            "header_status": workbook.add_format({
                "bold": True,
                "bg_color": "#1B6DE9",
                "font_color": "#FFFFFF",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }),
            "header_diff": workbook.add_format({
                "bold": True,
                "bg_color": "#E5FE00",
                "font_color": "#000000",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }),
            "text": workbook.add_format({
                "border": 1,
            }),
            "date": workbook.add_format({
                "border": 1,
                "num_format": "dd/mm/yyyy",
            }),
            "money": workbook.add_format({
                "border": 1,
                "num_format": '#,##0.00',
            }),
            "warning_money": workbook.add_format({
                "border": 1,
                "bg_color": "#FFF2CC",
                "num_format": '#,##0.00',
            }),
            "warning_text": workbook.add_format({
                "border": 1,
                "bg_color": "#FFF2CC",
            }),
            "warning_date": workbook.add_format({
                "border": 1,
                "bg_color": "#FFF2CC",
                "num_format": "dd/mm/yyyy",
            }),
            "boolean": workbook.add_format({
                "border": 1,
                "align": "center",
            }),
        }


    def _get_excel_headers(self):
        return [
            ("Tipo documento", "header_dian"),
            ("Folio", "header_dian"),
            ("Prefijo", "header_dian"),
            ("Fecha DIAN", "header_dian"),
            ("NIT emisor", "header_dian"),
            ("Nombre emisor", "header_dian"),
            ("IVA DIAN", "header_dian"),
            ("Total DIAN", "header_dian"),

            ("Proveedor encontrado", "header_odoo"),
            ("Factura Odoo", "header_odoo"),
            ("Referencia Odoo", "header_odoo"),
            ("Fecha Odoo", "header_odoo"),
            ("IVA Odoo", "header_odoo"),
            ("Total Odoo", "header_odoo"),

            ("Estado validación", "header_status"),
            ("Observación", "header_status"),
            ("Conciliado", "header_status"),

            ("Diferencia IVA", "header_diff"),
            ("Diferencia Total", "header_diff"),
        ]


    def _get_excel_column_widths(self):
        return {
            0: 22,
            1: 15,
            2: 15,
            3: 14,   # Fecha DIAN
            4: 18,
            5: 30,
            6: 14,
            7: 14,
            8: 28,
            9: 20,
            10: 20,
            11: 14,  # Fecha Odoo
            12: 14,
            13: 14,
            14: 18,
            15: 40,
            16: 12,
            17: 16,
            18: 16,
        }


    def _write_excel_line(self, sheet, row, line, formats):
        iva_dian = self._to_amount(line.iva)
        total_dian = self._to_amount(line.total)
        iva_odoo = self._to_amount(line.odoo_iva)
        total_odoo = self._to_amount(line.odoo_total)

        diff_iva = round(iva_dian - iva_odoo, 2)
        diff_total = round(total_dian - total_odoo, 2)

        has_iva_diff = abs(diff_iva) >= 0.01
        has_total_diff = abs(diff_total) >= 0.01

        fecha_dian = line.fecha_emision_dian
        fecha_odoo = line.fecha_factura_odoo
        has_date_diff = bool(fecha_dian and fecha_odoo and fecha_dian != fecha_odoo)

        iva_dian_fmt = formats["warning_money"] if has_iva_diff else formats["money"]
        iva_odoo_fmt = formats["warning_money"] if has_iva_diff else formats["money"]
        diff_iva_fmt = formats["warning_money"] if has_iva_diff else formats["money"]

        total_dian_fmt = formats["warning_money"] if has_total_diff else formats["money"]
        total_odoo_fmt = formats["warning_money"] if has_total_diff else formats["money"]
        diff_total_fmt = formats["warning_money"] if has_total_diff else formats["money"]

        fecha_dian_fmt = formats["warning_date"] if has_date_diff else formats["date"]
        fecha_odoo_fmt = formats["warning_date"] if has_date_diff else formats["date"]

        status_fmt = formats["warning_text"] if (has_iva_diff or has_total_diff or has_date_diff) else formats["text"]

        sheet.write(row, 0, line.tipo_documento or "", formats["text"])
        sheet.write(row, 1, line.folio or "", formats["text"])
        sheet.write(row, 2, line.prefijo or "", formats["text"])

        if fecha_dian:
            sheet.write_datetime(row, 3, datetime.combine(fecha_dian, datetime.min.time()), fecha_dian_fmt)
        else:
            sheet.write(row, 3, "", fecha_dian_fmt)

        sheet.write(row, 4, line.nit_emisor or "", formats["text"])
        sheet.write(row, 5, line.nombre_emisor or "", formats["text"])

        sheet.write_number(row, 6, iva_dian, iva_dian_fmt)
        sheet.write_number(row, 7, total_dian, total_dian_fmt)

        sheet.write(row, 8, line.partner_id.display_name if line.partner_id else "", formats["text"])
        sheet.write(row, 9, line.move_id.name if line.move_id else "", formats["text"])
        sheet.write(row, 10, line.odoo_ref or "", formats["text"])

        if fecha_odoo:
            sheet.write_datetime(row, 11, datetime.combine(fecha_odoo, datetime.min.time()), fecha_odoo_fmt)
        else:
            sheet.write(row, 11, "", fecha_odoo_fmt)

        sheet.write_number(row, 12, iva_odoo, iva_odoo_fmt)
        sheet.write_number(row, 13, total_odoo, total_odoo_fmt)

        sheet.write(row, 14, line.validation_status or "", status_fmt)
        sheet.write(row, 15, line.validation_note or "", status_fmt)
        sheet.write(row, 16, "Sí" if line.is_reconciled else "No", formats["boolean"])

        sheet.write_number(row, 17, diff_iva, diff_iva_fmt)
        sheet.write_number(row, 18, diff_total, diff_total_fmt)
    # ============================================================
    # Validated and processed action (no vuelta atrás)
    # ============================================================
    def action_process_validated(self):
        self.ensure_one()
        # Aquí podríamos agregar lógica adicional si es necesario, pero en este caso
        # simplemente cambiamos el estado a 'validated' para marcarlo como finalizado.
        self.state = "validated"


    # ============================================================
    # Open list of token file records
    # ============================================================
    def action_open_file_ids_list(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Registros del Token DIAN",
            "res_model": "mega.dian.token.file",
            "view_mode": "list,form",
            "domain": [("token_id", "=", self.id)],
            "context": {
                "default_token_id": self.id,
                "search_default_token_id": self.id,
            },
            "target": "current",
        }

    # ============================================================
    # Unlink override para evitar eliminación de tokens no borrador
    # ============================================================
    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_(
                    "No se puede eliminar el token DIAN '%s' porque su estado es '%s'. "
                    "Solo se permiten eliminaciones en estado Borrador."
                ) % (rec.name, rec.state))
        return super().unlink()

    # ============================================================
    # Unlink override para evitar eliminación de tokens no borrador
    # ============================================================
    def action_reset_to_draft(self):
        self.ensure_one()

        if self.state == "draft":
            raise UserError(_("El token ya se encuentra en estado Borrador."))

        self.state = "draft"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Token DIAN"),
                "message": _("El token volvió a estado Borrador."),
                "type": "success",
                "sticky": False,
            },
        }
