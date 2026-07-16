# -*- coding: utf-8 -*-
import io
import base64
import re
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

import xlsxwriter  # type: ignore

from odoo import api, fields, models, _  # type: ignore
from odoo.exceptions import UserError, AccessError, ValidationError  # type: ignore

_logger = logging.getLogger(__name__)


class MegaDianToken(models.Model):
    _name = "mega.dian.token"
    _description = "Token DIAN"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    _DIAN_TIPO_TO_MOVE_TYPE = {
        "Factura electrónica":                "in_invoice",
        "Nota de crédito electrónica":        "in_refund",
        "Documento soporte con no obligados": "in_invoice",
    }

    _GROUP_MANAGER = "mega_validator_token_dian.group_dian_manager"
    _GROUP_ADMIN = "mega_validator_token_dian.group_dian_admin"

    _SPANISH_MONTHS = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }

    name = fields.Char(
        string="Nombre del token",
        compute="_compute_name",
        store=True,
        tracking=True,
    )

    token_code = fields.Char(
        string="Consecutivo",
        readonly=True,
        copy=False,
        index=True,
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

    @api.depends("date_start", "date_end")
    def _compute_name(self):
        for rec in self:
            rec.name = rec._format_date_range(rec.date_start, rec.date_end)

    def _format_date_range(self, date_start, date_end):
        if not date_start or not date_end:
            return _("Nuevo Token DIAN")

        month_start = self._SPANISH_MONTHS.get(date_start.month, "")
        month_end = self._SPANISH_MONTHS.get(date_end.month, "")

        if date_start.year == date_end.year and date_start.month == date_end.month:
            return "%02d al %02d de %s del %s" % (
                date_start.day, date_end.day, month_start, date_start.year,
            )

        if date_start.year == date_end.year:
            return "%02d de %s al %02d de %s del %s" % (
                date_start.day, month_start, date_end.day, month_end, date_start.year,
            )

        return "%02d de %s del %s al %02d de %s del %s" % (
            date_start.day, month_start, date_start.year,
            date_end.day, month_end, date_end.year,
        )

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_(
                    "La fecha final (%(date_end)s) no puede ser anterior "
                    "a la fecha inicial (%(date_start)s)."
                ) % {"date_end": rec.date_end, "date_start": rec.date_start})

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
    # CONTROL DE PERMISOS (defensa en profundidad, no depender solo
    # del atributo groups= de las vistas: estos métodos son también
    # invocables por RPC/API directamente).
    # ============================================================
    def _check_dian_group(self, group_xmlid, action_label):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_(
                "No tienes permisos suficientes para %s. "
                "Solicita a un administrador que te asigne el rol correspondiente "
                "de Conciliación DIAN."
            ) % action_label)

    # ============================================================
    # PROCESAMIENTO / CONCILIACIÓN
    # ============================================================
    def action_process_token(self):
        self.ensure_one()
        self._check_dian_group(self._GROUP_MANAGER, _("procesar tokens DIAN"))

        if not self.file_ids:
            raise UserError(_("No existen registros para procesar en este token DIAN."))

        move_model = self.env["account.move"]
        partner_model = self.env["res.partner"]

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
        # Determinar el tipo de movimiento Odoo según el tipo documental DIAN
        move_type = self._get_move_type_for_document(line.tipo_documento)
        if not move_type:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_("Tipo de documento DIAN no soportado: %s") % (line.tipo_documento or ""),
                is_reconciled=False,
            )
            return False

        is_refund = (move_type == "in_refund")

        nit_emisor = self._normalize_text(line.nit_emisor)
        prefijo = self._normalize_text(line.prefijo)
        folio = self._normalize_text(line.folio)

        line_total = self._to_amount(line.total)
        line_iva = self._to_amount(line.iva)

        # No se busca ninguna factura sin un proveedor identificado de forma
        # inequívoca: NIT vacío, sin coincidencia o ambiguo NUNCA debe derivar
        # en una búsqueda entre todos los proveedores.
        if not nit_emisor:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_(
                    "El NIT emisor de la DIAN viene vacío; no fue posible identificar "
                    "al proveedor. No se realizó búsqueda de facturas."
                ),
                is_reconciled=False,
            )
            return False

        partners_found = self._find_partner_by_vat(partner_model, nit_emisor)

        if not partners_found:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_(
                    "No existe un proveedor en Odoo con NIT '%s'. "
                    "No se realizó búsqueda de facturas."
                ) % nit_emisor,
                is_reconciled=False,
            )
            return False

        if len(partners_found) > 1:
            self._write_line_result(
                line=line,
                status="not_found",
                note=_(
                    "Se encontraron %s proveedores distintos en Odoo con NIT '%s'. "
                    "No se realizó búsqueda de facturas; se requiere depurar el "
                    "maestro de terceros."
                ) % (len(partners_found), nit_emisor),
                is_reconciled=False,
            )
            return False

        partner = partners_found

        ref_candidates = self._build_reference_candidates(prefijo=prefijo, folio=folio)
        candidate_moves = self._find_candidate_moves(
            move_model=move_model, partner=partner, move_type=move_type
        )

        if not candidate_moves:
            self._write_line_result(
                line=line,
                status="not_found",
                note=(
                    _("No se encontraron notas crédito de proveedor para el NIT identificado.")
                    if is_refund
                    else _("No se encontraron facturas proveedor para el NIT identificado.")
                ),
                is_reconciled=False,
            )
            return False

        # 1) Coincidencia por referencia
        reference_matches = candidate_moves.filtered(
            lambda m: self._match_reference(m, ref_candidates)
        )

        if not reference_matches:
            self._write_line_result(
                line=line,
                status="not_found",
                note=(
                    _("No se encontró nota crédito en Odoo con referencia coincidente.")
                    if is_refund
                    else _("No se encontró factura en Odoo con referencia coincidente.")
                ),
                is_reconciled=False,
            )
            return False

        # 2) Coincidencia exacta: referencia + IVA + total ajustado (sin retenciones)
        exact_matches = reference_matches.filtered(
            lambda m: self._amounts_equal_with_tolerance(self._get_move_dian_iva(m), line_iva)
            and self._amounts_equal_with_tolerance(self._get_move_dian_total_adjusted(m), line_total)
        )

        if len(exact_matches) == 1:
            self._write_line_match(
                line=line,
                move=exact_matches[0],
                status="matched",
                note=(
                    _("Coincidencia exacta de nota crédito por NIT, referencia, IVA y total.")
                    if is_refund
                    else _("Coincidencia exacta por NIT, referencia, IVA y total antes de retenciones.")
                ),
                is_reconciled=True,
            )
            return True

        if len(exact_matches) > 1:
            self._write_line_result(
                line=line,
                status="multiple",
                note=(
                    _("Se encontraron múltiples notas crédito con coincidencia exacta.")
                    if is_refund
                    else _("Se encontraron múltiples facturas con coincidencia exacta.")
                ),
                is_reconciled=False,
            )
            return False

        # 3) Coincidencia parcial por referencia + IVA
        partial_by_iva = reference_matches.filtered(
            lambda m: self._amounts_equal_with_tolerance(self._get_move_dian_iva(m), line_iva)
        )

        if len(partial_by_iva) == 1:
            self._write_line_match(
                line=line,
                move=partial_by_iva[0],
                status="partial",
                note=(
                    _("La nota crédito coincide por NIT, referencia e IVA, pero no el total.")
                    if is_refund
                    else _("Coincide NIT, referencia e IVA, pero no el total.")
                ),
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

        # 4) Coincidencia parcial por referencia + total ajustado (sin retenciones)
        partial_by_total = reference_matches.filtered(
            lambda m: self._amounts_equal_with_tolerance(self._get_move_dian_total_adjusted(m), line_total)
        )

        if len(partial_by_total) == 1:
            self._write_line_match(
                line=line,
                move=partial_by_total[0],
                status="partial",
                note=(
                    _("La nota crédito coincide por NIT, referencia y total, pero no el IVA.")
                    if is_refund
                    else _("Coincide NIT, referencia y total, pero no el IVA.")
                ),
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

        # 5) Coincidencia solo por referencia — montos no coinciden.
        # Prohibido elegir un candidato arbitrario: con más de un candidato
        # por referencia, el resultado debe ser "multiple", nunca tomar
        # reference_matches[0] silenciosamente.
        if len(reference_matches) > 1:
            self._write_line_result(
                line=line,
                status="multiple",
                note=(
                    _("Se encontraron múltiples notas crédito candidatas por referencia, "
                      "sin coincidencia de IVA ni total.")
                    if is_refund
                    else _("Se encontraron múltiples facturas candidatas por referencia, "
                           "sin coincidencia de IVA ni total.")
                ),
                is_reconciled=False,
            )
            return False

        if len(reference_matches) == 1:
            self._write_line_match(
                line=line,
                move=reference_matches,
                status="partial",
                note=(
                    _("La nota crédito coincide por referencia, pero el IVA o el total no coincide.")
                    if is_refund
                    else _("La referencia coincide, pero los valores de IVA y total no coinciden exactamente.")
                ),
                is_reconciled=False,
            )
            return False

        self._write_line_result(
            line=line,
            status="not_found",
            note=_("No se encontró documento en Odoo con coincidencia suficiente."),
            is_reconciled=False,
        )
        return False

    def _get_move_type_for_document(self, tipo_documento):
        """
        Retorna el move_type de Odoo para el tipo DIAN.
        Devuelve None si el tipo no está soportado para no conciliar silenciosamente.
        """
        return self._DIAN_TIPO_TO_MOVE_TYPE.get(tipo_documento)

    def _find_partner_by_vat(self, partner_model, vat):
        """
        Retorna TODOS los terceros que coinciden con el NIT (sin limit=1),
        para que el llamador pueda detectar ambigüedad y evitar elegir uno
        arbitrariamente. La normalización avanzada del NIT (dígito de
        verificación, contactos comerciales/hijos) queda para una fase
        posterior; aquí solo se corrige la selección automática silenciosa.
        """
        if not vat:
            return partner_model.browse()
        return partner_model.search([("vat", "ilike", vat)])

    def _find_candidate_moves(self, move_model, partner, move_type="in_invoice"):
        domain = [
            ("move_type", "=", move_type),
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

    def _get_move_dian_other_taxes(self, move):
        """
        Retorna impuestos diferentes al IVA en formato texto,
        conservando el signo contable original.
        """
        impuestos = []

        for line in move.line_ids.filtered(lambda l: l.tax_line_id):
            tax = line.tax_line_id
            tax_name = (tax.name or "").lower()

            # Excluir IVA
            if "iva" in tax_name:
                continue

            amount = line.amount_currency if line.currency_id else line.balance

            if not amount:
                continue

            impuestos.append(
                f"{tax.name}: ${amount:,.2f}"
            )

        return "\n".join(impuestos) if impuestos else ""

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
                "odoo_total_adjusted": self._get_move_dian_total_adjusted(move),
                "odoo_iva": self._get_move_dian_iva(move),
                "impuestos_info": self._get_move_dian_other_taxes(move),
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

    def _amounts_equal_with_tolerance(self, left, right):
        """
        Compara montos con la tolerancia acordada de negocio: diferencia
        absoluta <= $500 COP. Se usa tanto para IVA como para Total, de
        forma que una diferencia de unos pocos pesos en cualquiera de los
        dos no impida marcar el documento como conciliado.
        """
        diff = abs(Decimal(str(left or 0.0)) - Decimal(str(right or 0.0)))
        return diff <= Decimal("500.00")

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

        # 2b. El folio DIAN puede incluir dígitos de prefijo de resolución que el
        #     proveedor no registra en su referencia interna.
        #     Ej: DIAN folio "3027849" → Odoo ref "027849" ("3027849".endswith("027849")).
        #     Protección: solo aplica si la ref Odoo tiene 5+ dígitos para evitar
        #     coincidencias accidentales con sufijos cortos.
        if move_ref_digits and len(move_ref_digits) >= 5:
            for cand_digits in candidate_digits:
                if cand_digits and cand_digits.endswith(move_ref_digits):
                    return True

        if move_name_digits and len(move_name_digits) >= 5:
            for cand_digits in candidate_digits:
                if cand_digits and cand_digits.endswith(move_name_digits):
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
        Retorna el IVA del documento como valor absoluto.
        Para in_invoice: líneas IVA tienen balance positivo (débito).
        Para in_refund: líneas IVA tienen balance negativo (crédito, asiento inverso).
        En ambos casos se retorna el valor absoluto para comparar contra DIAN.
        """
        iva_amount = 0.0
        is_refund = move.move_type == "in_refund"

        for line in move.line_ids.filtered(lambda l: l.tax_line_id):
            tax_name = (line.tax_line_id.name or "").lower()
            if "iva" not in tax_name:
                continue
            amount = line.amount_currency if line.currency_id else line.balance
            if is_refund:
                iva_amount += abs(amount or 0.0)
            elif (amount or 0.0) > 0:
                iva_amount += abs(amount or 0.0)

        return iva_amount

    def _get_move_dian_other_taxes_amount(self, move):
        """
        Retorna la suma de impuestos diferentes al IVA.
        Conserva el signo: retenciones negativas, impuestos positivos.
        """
        other_taxes_amount = 0.0

        for line in move.line_ids.filtered(lambda l: l.tax_line_id):
            tax_name = (line.tax_line_id.name or "").lower()

            if "iva" in tax_name:
                continue

            amount = line.amount_currency if line.currency_id else line.balance

            if amount:
                other_taxes_amount += amount

        return other_taxes_amount


    def _get_move_dian_total(self, move):
        """
        Total Odoo = subtotal + IVA + otros impuestos (incluye retenciones negativas).
        Se usa para mostrar el total real contable de Odoo, no para comparar contra DIAN.
        """
        untaxed = move.amount_untaxed or 0.0
        iva_amount = self._get_move_dian_iva(move)
        other_taxes_amount = self._get_move_dian_other_taxes_amount(move)

        return untaxed + iva_amount + other_taxes_amount

    def _is_retention_line(self, line):
        """
        Determina si una línea de impuesto es una retención.
        Criterio primario: porcentaje negativo en la definición del impuesto.
        Criterio de respaldo: nombre del impuesto.
        """
        tax = line.tax_line_id
        if not tax:
            return False
        if tax.amount_type in ('percent', 'fixed', 'division') and tax.amount < 0:
            return True
        name_lower = (tax.name or '').lower()
        return any(kw in name_lower for kw in ('rete', 'rte', 'retención', 'retencion', 'withhold'))

    def _get_move_dian_total_adjusted(self, move):
        """
        Total comparable con DIAN: base + IVA + impuestos no-IVA no-retención.
        Excluye retenciones porque el total DIAN es el valor bruto antes de retenciones.
        Para in_refund, las líneas de impuesto tienen signo inverso al de in_invoice;
        se usa abs() para normalizar sin alterar los datos contables del movimiento.
        """
        untaxed = move.amount_untaxed or 0.0
        iva_amount = self._get_move_dian_iva(move)
        is_refund = move.move_type == "in_refund"

        other_non_retention = 0.0
        for line in move.line_ids.filtered(lambda l: l.tax_line_id):
            if 'iva' in (line.tax_line_id.name or '').lower():
                continue
            if self._is_retention_line(line):
                continue
            amount = line.amount_currency if line.currency_id else line.balance
            if amount:
                if is_refund:
                    other_non_retention += abs(amount)
                else:
                    other_non_retention += amount

        return untaxed + iva_amount + other_non_retention

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
        self._check_dian_group(self._GROUP_MANAGER, _("exportar el token DIAN a Excel"))

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
            ("Tipo documento", "header_dian"),       # 0
            ("Folio", "header_dian"),                # 1
            ("Prefijo", "header_dian"),              # 2
            ("Fecha DIAN", "header_dian"),           # 3
            ("NIT emisor", "header_dian"),           # 4
            ("Nombre emisor", "header_dian"),        # 5
            ("IVA DIAN", "header_dian"),             # 6
            ("Total DIAN", "header_dian"),           # 7
            ("CUFE", "header_dian"),                 # 8

            ("Proveedor encontrado", "header_odoo"), # 9
            ("Factura Odoo", "header_odoo"),         # 10
            ("Referencia Odoo", "header_odoo"),      # 11
            ("Fecha Odoo", "header_odoo"),           # 12
            ("IVA Odoo", "header_odoo"),             # 13
            ("Impuestos", "header_odoo"),            # 14
            ("Total Odoo", "header_odoo"),           # 15
            ("Total Odoo ajustado", "header_odoo"),  # 16 — sin retenciones

            ("Estado validación", "header_status"),  # 17
            ("Observación", "header_status"),        # 18
            ("Conciliado", "header_status"),         # 19

            ("Diferencia IVA", "header_diff"),       # 20
            ("Diferencia Total", "header_diff"),     # 21 — calculada sobre total ajustado
        ]


    def _get_excel_column_widths(self):
        return {
            0: 22,
            1: 15,
            2: 15,
            3: 14,
            4: 18,
            5: 30,
            6: 14,
            7: 14,
            8: 55,   # CUFE
            9: 28,
            10: 20,
            11: 20,
            12: 14,
            13: 14,  # IVA Odoo
            14: 35,  # Impuestos
            15: 14,  # Total Odoo (con retenciones)
            16: 20,  # Total Odoo ajustado (sin retenciones)
            17: 18,  # Estado validación
            18: 40,  # Observación
            19: 12,  # Conciliado
            20: 16,  # Diferencia IVA
            21: 16,  # Diferencia Total (sobre total ajustado)
        }


    def _write_excel_line(self, sheet, row, line, formats):
        iva_dian = self._to_amount(line.iva)
        total_dian = self._to_amount(line.total)
        iva_odoo = self._to_amount(line.odoo_iva)
        total_odoo = self._to_amount(line.odoo_total)
        total_odoo_adjusted = self._to_amount(line.odoo_total_adjusted)

        diff_iva = round(iva_dian - iva_odoo, 2)
        diff_total = round(total_dian - total_odoo_adjusted, 2)

        # Mismo umbral de tolerancia de negocio ($500 COP) usado en la
        # conciliación (_amounts_equal_with_tolerance), para que el resaltado
        # visual del Excel sea consistente con el estado de validación.
        has_iva_diff = abs(diff_iva) > 500.00
        has_total_diff = abs(diff_total) > 500.00

        fecha_dian = line.fecha_emision_dian
        fecha_odoo = line.fecha_factura_odoo
        has_date_diff = bool(fecha_dian and fecha_odoo and fecha_dian != fecha_odoo)

        iva_dian_fmt = formats["warning_money"] if has_iva_diff else formats["money"]
        iva_odoo_fmt = formats["warning_money"] if has_iva_diff else formats["money"]
        diff_iva_fmt = formats["warning_money"] if has_iva_diff else formats["money"]

        total_dian_fmt = formats["warning_money"] if has_total_diff else formats["money"]
        total_odoo_fmt = formats["money"]
        total_odoo_adj_fmt = formats["warning_money"] if has_total_diff else formats["money"]
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
        sheet.write(row, 8, line.cufe or "", formats["text"])

        sheet.write(row, 9, line.partner_id.display_name if line.partner_id else "", formats["text"])
        sheet.write(row, 10, line.move_id.name if line.move_id else "", formats["text"])
        sheet.write(row, 11, line.odoo_ref or "", formats["text"])

        if fecha_odoo:
            sheet.write_datetime(row, 12, datetime.combine(fecha_odoo, datetime.min.time()), fecha_odoo_fmt)
        else:
            sheet.write(row, 12, "", fecha_odoo_fmt)

        sheet.write_number(row, 13, iva_odoo, iva_odoo_fmt)
        sheet.write(row, 14, line.impuestos_info or "", formats["text"])
        sheet.write_number(row, 15, total_odoo, total_odoo_fmt)
        sheet.write_number(row, 16, total_odoo_adjusted, total_odoo_adj_fmt)

        sheet.write(row, 17, line.validation_status or "", status_fmt)
        sheet.write(row, 18, line.validation_note or "", status_fmt)
        sheet.write(row, 19, "Sí" if line.is_reconciled else "No", formats["boolean"])

        sheet.write_number(row, 20, diff_iva, diff_iva_fmt)
        sheet.write_number(row, 21, diff_total, diff_total_fmt)

    # ============================================================
    # Validated and processed action (no vuelta atrás)
    # ============================================================
    def action_process_validated(self):
        self.ensure_one()
        self._check_dian_group(self._GROUP_MANAGER, _("validar tokens DIAN"))
        if not self.file_ids:
            raise UserError(_("No hay registros para validar en este Token DIAN."))
        if any(line.validation_status == "pending" for line in self.file_ids):
            raise UserError(_(
                "No se puede validar: existen registros sin procesar (estado Pendiente). "
                "Debes ejecutar 'Procesar' antes de validar."
            ))
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
    # "name" es 100% calculado a partir de date_start/date_end: se
    # descarta cualquier valor recibido para ese campo, incluso por
    # RPC/API directo, para que nunca quede desincronizado de las
    # fechas (no depender solo de que la vista lo muestre sin widget).
    # "token_code" es el consecutivo asignado por ir.sequence al crear.
    # ============================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop("name", None)
            vals.pop("token_code", None)
            vals["token_code"] = self.env["ir.sequence"].next_by_code(
                "mega.dian.token"
            ) or _("Nuevo")
        return super().create(vals_list)

    def write(self, vals):
        vals.pop("name", None)
        vals.pop("token_code", None)
        return super().write(vals)

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
        self._check_dian_group(self._GROUP_ADMIN, _("devolver tokens DIAN a borrador"))

        if self.state == "draft":
            raise UserError(_("El token ya se encuentra en estado Borrador."))

        self.state = "draft"
