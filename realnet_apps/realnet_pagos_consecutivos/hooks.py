from odoo import api, SUPERUSER_ID


def _compute_next_from_max(env, seq_xmlid: str, prefix: str, model: str, number_field: str):
    seq = env.ref(seq_xmlid, raise_if_not_found=False)
    if not seq:
        return
    # Find the maximum existing number for this prefix in the given model/field
    cr = env.cr
    cr.execute(
        f"""
        SELECT MAX(SUBSTRING({number_field} FROM '\\d+'))::int AS max_num
        FROM {model}
        WHERE {number_field} IS NOT NULL AND {number_field} LIKE %s
        """,
        (prefix + '%',),
    )
    row = cr.fetchone()
    max_num = row and row[0] or 0
    # If DB has greater number than sequence, bump sequence
    if max_num and seq.number_next <= max_num:
        seq.sudo().write({"number_next": max_num + 1})


# Odoo 18 passes a single env argument to post-init hooks
def post_init_sync_ceci_sequences(env):
    # CE for outbound
    _compute_next_from_max(env, "realnet_pagos_consecutivos.seq_payment_ce", "CE", "account_payment", "x_ceci_number")
    # CI for inbound
    _compute_next_from_max(env, "realnet_pagos_consecutivos.seq_payment_ci", "CI", "account_payment", "x_ceci_number")

    # Backfill missing numbers on already posted payments
    Payment = env["account.payment"].sudo()
    missing = Payment.search([("state", "=", "posted"), ("x_ceci_number", "=", False)])
    if missing:
        missing._assign_ceci_number_if_needed()
