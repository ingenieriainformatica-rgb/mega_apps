# -*- coding: utf-8 -*-
import io
import logging
from odoo import http, fields  #type: ignore
from odoo.http import request  #type: ignore
from .services.sales import (
    get_partner_autocomplete,
    get_facturacion_report
)  #type: ignore

try:
    import xlsxwriter  #type: ignore
except Exception:
    xlsxwriter = None

_logger = logging.getLogger(__name__)


class PartnerLedgerController(http.Controller):

    @http.route("/mega_partner_ledger/export", type="http", auth="user", website=False, csrf=False)
    def export_ledger(self, documento=None, date_from=None, date_to=None, **kwargs):
        # 1) Validaciones básicas
        if not documento:
            return request.make_response(
                "Falta parámetro 'documento' (partner_id).",
                headers=[("Content-Type", "text/plain; charset=utf-8")],
                status=400,
            )

        # Normaliza fechas
        if not date_from:
            date_from = fields.Date.to_string(fields.Date.context_today(request.env))
        if not date_to:
            date_to = fields.Date.to_string(fields.Date.context_today(request.env))

        if not xlsxwriter:
            return request.make_response(
                "No está disponible xlsxwriter en el servidor.",
                headers=[("Content-Type", "text/plain; charset=utf-8")],
                status=500,
            )

        # 2) Traer data (igual que tu dashboard)
        data = get_facturacion_report(
            partner_id=documento,
            date_from=date_from,
            date_to=date_to,
        )

        partner = (data or {}).get("partner") or {}
        moves = (data or {}).get("moves") or []

        # 3) Construir XLSX en memoria
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})

        # =========================
        # Formatos
        # =========================
        f_hdr = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        f_hdr_dark = wb.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
        f_kv_key = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        f_kv_val = wb.add_format({"border": 1})

        f_txt = wb.add_format({"border": 1})
        f_txt_wrap = wb.add_format({"border": 1, "text_wrap": True, "valign": "top"})
        f_money = wb.add_format({"num_format": "#,##0.00", "border": 1})
        f_money_bold = wb.add_format({"num_format": "#,##0.00", "border": 1, "bold": True, "bg_color": "#FFF2CC"})
        f_date = wb.add_format({"num_format": "yyyy-mm-dd", "border": 1})

        f_section = wb.add_format({"bold": True, "bg_color": "#FFE699", "border": 1})
        f_invoice_band = wb.add_format({"bold": True, "bg_color": "#E2EFDA", "border": 1})
        f_invoice_band_wrap = wb.add_format({"bold": True, "bg_color": "#E2EFDA", "border": 1, "text_wrap": True})

        # =========================
        # Hoja 1: Facturas (con bloque de cuentas por factura)
        # =========================
        ws1 = wb.add_worksheet("Facturas")

        # Encabezado (key/value)
        ws1.write(0, 0, "Tercero", f_kv_key)
        ws1.write(0, 1, partner.get("name") or "", f_kv_val)
        ws1.write(1, 0, "NIT", f_kv_key)
        ws1.write(1, 1, partner.get("vat") or "", f_kv_val)
        ws1.write(2, 0, "Desde", f_kv_key)
        ws1.write(2, 1, date_from or "", f_kv_val)
        ws1.write(3, 0, "Hasta", f_kv_key)
        ws1.write(3, 1, date_to or "", f_kv_val)

        row = 5

        # Tabla resumen facturas
        headers = ["Ref", "Diario", "Fecha", "Vence", "Moneda", "Subtotal", "Impuestos", "Total", "Estado pago"]
        for col, h in enumerate(headers):
            ws1.write(row, col, h, f_hdr)
        row += 1

        # helper: normaliza texto de cuenta "código nombre"
        def _fmt_account(l):
            code = (l.get("account_code") or "").strip()
            name = (l.get("account_name") or "").strip()
            if code and name:
                return f"{code} {name}"
            return code or name or ""

        # helper: distribución analítica si viene
        # - Puede venir como string ya formateado, o como dict (analytic_distribution)
        def _fmt_distribution(l):
            dist = l.get("distribution")  # si tu servicio ya lo manda así
            if dist:
                return str(dist)

            dist2 = l.get("analytic_distribution")
            if isinstance(dist2, dict):
                # Ej: {"12": 50, "44": 50} => "12:50%, 44:50%"
                parts = []
                for k, v in dist2.items():
                    try:
                        vv = float(v)
                        parts.append(f"{k}:{vv:.0f}%")
                    except Exception:
                        parts.append(f"{k}:{v}")
                return ", ".join(parts)
            return ""

        # Por cada factura: fila de resumen + bloque tipo “cuadro rojo” debajo
        for m in moves:
            ref = (m.get("ref") or m.get("name") or "").strip()
            journal = (m.get("journal") or "").strip()
            inv_date = m.get("invoice_date") or ""
            due = m.get("invoice_date_due") or ""
            currency = (m.get("currency") or "").strip()

            untaxed = float(m.get("amount_untaxed") or 0)
            tax = float(m.get("amount_tax") or 0)
            total = float(m.get("amount_total") or 0)
            pay_state = (m.get("payment_state") or "").strip()

            # Resumen de factura (una fila)
            ws1.write(row, 0, ref, f_txt)
            ws1.write(row, 1, journal, f_txt)
            ws1.write(row, 2, inv_date, f_txt)
            ws1.write(row, 3, due, f_txt)
            ws1.write(row, 4, currency, f_txt)
            ws1.write_number(row, 5, untaxed, f_money)
            ws1.write_number(row, 6, tax, f_money)
            ws1.write_number(row, 7, total, f_money_bold)
            ws1.write(row, 8, pay_state, f_txt)
            row += 1

            # Bloque “Apuntes contables” (tipo cuadro rojo)
            ws1.write(row, 0, "Apuntes contables", f_section)
            # merge a lo ancho de la tabla (0..8)
            ws1.merge_range(row, 0, row, 8, "Apuntes contables", f_section)
            row += 1

            # Header del bloque (igual a Odoo)
            acc_headers = ["Cuenta", "Etiqueta", "Distribución", "Débito", "Crédito"]
            ws1.write(row, 0, acc_headers[0], f_hdr_dark)
            ws1.write(row, 1, acc_headers[1], f_hdr_dark)
            ws1.write(row, 2, acc_headers[2], f_hdr_dark)
            ws1.write(row, 3, acc_headers[3], f_hdr_dark)
            ws1.write(row, 4, acc_headers[4], f_hdr_dark)

            # Pintamos una banda suave en columnas 5..8 para que no se vea “cortado”
            for c in range(5, 9):
                ws1.write(row, c, "", f_hdr_dark)
            row += 1

            lines = m.get("lines") or []
            if not lines:
                ws1.merge_range(row, 0, row, 8, "Sin apuntes contables en el reporte.", f_txt)
                row += 1
            else:
                for l in lines:
                    cuenta = _fmt_account(l)
                    etiqueta = (l.get("name") or "").strip()
                    distrib = _fmt_distribution(l)
                    debit = float(l.get("debit") or 0)
                    credit = float(l.get("credit") or 0)

                    ws1.write(row, 0, cuenta, f_txt_wrap)
                    ws1.write(row, 1, etiqueta, f_txt_wrap)
                    ws1.write(row, 2, distrib, f_txt_wrap)
                    ws1.write_number(row, 3, debit, f_money)
                    ws1.write_number(row, 4, credit, f_money)

                    # “relleno” hasta col 8 para que el bloque se vea alineado
                    ws1.write(row, 5, "", f_txt)
                    ws1.write(row, 6, "", f_txt)
                    ws1.write(row, 7, "", f_txt)
                    ws1.write(row, 8, "", f_txt)
                    row += 1

            # Espacio entre facturas (1 fila)
            row += 1

        # Anchos de columnas
        ws1.set_column(0, 0, 40)  # Cuenta / Ref
        ws1.set_column(1, 1, 28)  # Diario / Etiqueta
        ws1.set_column(2, 2, 24)  # Distribución
        ws1.set_column(3, 4, 14)  # Débito / Crédito
        ws1.set_column(5, 5, 12)  # Subtotal (cuando está en resumen)
        ws1.set_column(6, 6, 12)  # Impuestos
        ws1.set_column(7, 7, 14)  # Total
        ws1.set_column(8, 8, 14)  # Estado pago

        ws1.freeze_panes(6, 0)  # Congela encabezados (fila 6 aprox)

        # =========================
        # Hoja 2: Apuntes (plano)
        # =========================
        ws2 = wb.add_worksheet("Apuntes")
        row2 = 0
        headers2 = ["Ref", "Fecha", "Cuenta", "Nombre cuenta", "Etiqueta/Detalle", "Distribución", "Débito", "Crédito", "Balance"]
        for col, h in enumerate(headers2):
            ws2.write(row2, col, h, f_hdr)
        row2 += 1

        for m in moves:
            ref = (m.get("ref") or m.get("name") or "").strip()
            for l in (m.get("lines") or []):
                ws2.write(row2, 0, ref, f_txt)
                ws2.write(row2, 1, l.get("date") or "", f_txt)
                ws2.write(row2, 2, (l.get("account_code") or ""), f_txt)
                ws2.write(row2, 3, (l.get("account_name") or ""), f_txt_wrap)
                ws2.write(row2, 4, (l.get("name") or ""), f_txt_wrap)
                ws2.write(row2, 5, _fmt_distribution(l), f_txt_wrap)
                ws2.write_number(row2, 6, float(l.get("debit") or 0), f_money)
                ws2.write_number(row2, 7, float(l.get("credit") or 0), f_money)
                ws2.write_number(row2, 8, float(l.get("balance") or 0), f_money)
                row2 += 1

        ws2.set_column(0, 0, 16)
        ws2.set_column(1, 1, 12)
        ws2.set_column(2, 2, 12)
        ws2.set_column(3, 3, 40)
        ws2.set_column(4, 4, 55)
        ws2.set_column(5, 5, 26)
        ws2.set_column(6, 8, 14)
        ws2.freeze_panes(1, 0)

        wb.close()
        output.seek(0)

        # 4) Respuesta HTTP para descargar
        safe_partner = (partner.get("name") or "partner").replace(" ", "_")
        filename = f"ledger_{safe_partner}_{date_from}_{date_to}.xlsx"
        headers = [
            ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
        ]
        return request.make_response(output.read(), headers=headers)

    @http.route("/rn_partner_ledger/search", type="json", auth="user")
    def rn_partner_ledger_search(self, documento, tipo="all", date_from=None, date_to=None):
        try:
            data = get_facturacion_report(
                partner_id=documento,
                date_from=date_from,
                date_to=date_to,
            )
            return {"ok": True, "data": data}
        except Exception as e:
            _logger.exception("Error en /mega_partner_ledger/report")
            return {"ok": False, "error": str(e)}

    @http.route("/mega_partner_ledger/partner_autocomplete", type="json", auth="user")
    def partner_autocomplete(self, query="", tipo="all", limit=10):
        try:
            data = get_partner_autocomplete(
                query=query,
                tipo=tipo,
                limit=limit
            )
            return {"ok": True, "data": data}
        except Exception as e:
            _logger.exception("Error en /mega_partner_ledger/partner_autocomplete")
            return {"ok": False, "error": str(e)}