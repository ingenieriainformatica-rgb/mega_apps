import logging
from odoo.http import request  #type: ignore
from odoo import http, fields  #type: ignore

_logger = logging.getLogger(__name__)


def get_facturacion_report(partner_id=None, date_from=None, date_to=None):
    if not partner_id:
        return {"partner": None, "date_from": date_from, "date_to": date_to, "moves": []}

    if not date_from:
        date_from = fields.Date.to_string(fields.Date.context_today(request.env))
    if not date_to:
        date_to = fields.Date.to_string(fields.Date.context_today(request.env))

    env = request.env  # auth="user" => ya es el usuario logueado
    partner = env["res.partner"].browse(int(partner_id)).exists()
    if not partner:
        return {"partner": None, "date_from": date_from, "date_to": date_to, "moves": []}

    partner_data = {
        "id": partner.id,
        "name": partner.display_name,
        "vat": partner.vat,
        "street": partner.street,
        "street2": partner.street2,
        "city": partner.city,
        "state": partner.state_id.name if partner.state_id else None,
        "country": partner.country_id.name if partner.country_id else None,
        "phone": partner.phone,
        "mobile": partner.mobile,
        "email": partner.email,
    }

    invoice_domain = [
        ("partner_id", "=", partner.id),
        ("move_type", "in", ("out_invoice", "out_refund")),
        ("state", "=", "posted"),
        ("invoice_date", ">=", date_from),
        ("invoice_date", "<=", date_to),
    ]
    moves = env["account.move"].search(invoice_domain, order="invoice_date asc, id asc")

    moves_payload = []
    MoveLine = env["account.move.line"]

    for m in moves:
        # 👇 Apuntes contables (lo que ves en “Apuntes contables”)
        aml_domain = [
            ("move_id", "=", m.id),
        ]
        amls = MoveLine.search(aml_domain, order="id asc")

        line_payload = []
        for l in amls:
            line_payload.append({
                "id": l.id,
                "date": fields.Date.to_string(l.date) if l.date else None,
                "account_id": l.account_id.id,
                "account_code": l.account_id.code,
                "account_name": l.account_id.display_name,
                "name": l.name,
                "debit": l.debit,
                "credit": l.credit,
                "balance": l.balance,
                "analytic": l.analytic_distribution or {},
            })

        moves_payload.append({
            "id": m.id,
            "ref": m.name,  # <-- referencia (FCE71937 etc.)
            "move_type": m.move_type,
            "invoice_date": fields.Date.to_string(m.invoice_date) if m.invoice_date else None,
            "invoice_date_due": fields.Date.to_string(m.invoice_date_due) if m.invoice_date_due else None,
            "journal": m.journal_id.name,
            "currency": m.currency_id.name,
            "amount_untaxed": m.amount_untaxed,
            "amount_tax": m.amount_tax,
            "amount_total": m.amount_total,
            "payment_state": m.payment_state,
            "lines": line_payload,  # ✅ aquí ya vienen las cuentas por factura
        })

    # Si además la quieres “como clave”, te la dejo lista así:
    by_ref = {m["ref"]: m for m in moves_payload}

    return {
        "partner": partner_data,
        "date_from": date_from,
        "date_to": date_to,
        "moves": moves_payload,   # lista
        "by_ref": by_ref,         # diccionario por referencia
    }

def get_partner_autocomplete(query="", tipo="all", limit=10):
    query = (query or "").strip()
    Partner = request.env["res.partner"].with_context(active_test=False)

    domain = [("active", "in", [True, False])]

    if query:
        domain += ["|", "|",
                    ("name", "ilike", query),
                    ("vat", "ilike", query),
                    ("ref", "ilike", query)]

    partners = Partner.search(domain, limit=int(limit), order="is_company desc, name asc")

    return [{
        "id": p.id,
        "name": p.display_name,
        "vat": p.vat,
        "ref": p.ref,
        "is_company": p.is_company,
    } for p in partners]
