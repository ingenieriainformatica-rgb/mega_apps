from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError  # type:ignore


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Número global CE/CI único (solo se asigna al posteo).
    x_ceci_number = fields.Char(
        string="CE/CI Number",
        readonly=True,
        copy=False,
        index=True,
        help="Consecutivo global: CE para pagos outbound (Send) y CI para pagos inbound (Receive).",
    )

    # Compatibilidad con vistas externas que esperan campos separados
    x_ce_number = fields.Char(
        string="CE Number",
        readonly=True,
        compute="_compute_x_ceci_compat",
        store=False,
        help="Número CE (solo cuando el pago es outbound).",
    )
    x_ci_number = fields.Char(
        string="CI Number",
        readonly=True,
        compute="_compute_x_ceci_compat",
        store=False,
        help="Número CI (solo cuando el pago es inbound).",
    )

    # Tipo para filtros/reportes
    x_ceci_type = fields.Selection(
        [
            ("ce", "CE"),
            ("ci", "CI"),
        ],
        string="Tipo CE/CI",
        readonly=True,
        copy=False,
        help="Tipo del consecutivo asignado según Payment Type al validar.",
    )

    # Campo para mostrar en vistas como identificador principal.
    x_ceci_display = fields.Char(
        string="Número (CE/CI / Interno)",
        compute="_compute_x_ceci_display",
        help="Muestra CE/CI si existe; en caso contrario el número interno (name).",
        store=False,
    )

    _sql_constraints = [
        (
            "x_ceci_number_unique",
            "unique(x_ceci_number)",
            "El número CE/CI debe ser único.",
        ),
    ]

    @api.depends("x_ceci_number", "name")
    def _compute_x_ceci_display(self):
        for rec in self:
            rec.x_ceci_display = rec.x_ceci_number or rec.name or ""

    @api.depends("x_ceci_number", "x_ceci_type")
    def _compute_x_ceci_compat(self):
        for rec in self:
            rec.x_ce_number = rec.x_ceci_number if rec.x_ceci_type == "ce" else False
            rec.x_ci_number = rec.x_ceci_number if rec.x_ceci_type == "ci" else False

    # --- Secuencias ---
    def _next_ceci_sequence(self, payment_type):
        if payment_type == "outbound":
            seq_code = "l10n_co.payment.ce"
            xmlid = "realnet_pagos_consecutivos.seq_payment_ce"
        elif payment_type == "inbound":
            seq_code = "l10n_co.payment.ci"
            xmlid = "realnet_pagos_consecutivos.seq_payment_ci"
        else:
            return False, False

        # Buscar por xmlid primero
        seq = self.env.ref(xmlid, raise_if_not_found=False)
        if not seq:
            seq = self.env["ir.sequence"].search([
                ("code", "=", seq_code),
                ("company_id", "in", [self.env.company.id, False]),
            ], limit=1, order="company_id desc")
        if not seq:
            raise ValidationError(_("No se encontró la secuencia requerida (%s). Actualice el módulo.") % seq_code)

        # Importante: usar la secuencia localizada por ID para evitar conflictos cuando existen
        # varias secuencias con el mismo code en diferentes compañías.
        number = seq.next_by_id() if hasattr(seq, "next_by_id") else self.env["ir.sequence"].next_by_code(seq_code)
        return number, ("ce" if payment_type == "outbound" else "ci")

    # --- Asignación principal ---
    def _assign_ceci_number_if_needed(self):
        for payment in self:
            if payment.x_ceci_number:
                continue  # Idempotencia
            if payment.payment_type not in ("outbound", "inbound"):
                continue  # transfer u otros -> se omite

            # Reintentos para manejar posibles colisiones de unicidad por concurrencia
            last_err = None
            number = False
            ctype = False
            for _attempt in range(5):
                number, ctype = payment.with_company(payment.company_id)._next_ceci_sequence(payment.payment_type)
                if not number:
                    break
                try:
                    with self.env.cr.savepoint():
                        payment.sudo().write({
                            "x_ceci_number": number,
                            "x_ceci_type": ctype,
                        })
                    last_err = None
                    break  # éxito
                except IntegrityError as e:
                    last_err = e
                    continue
            if last_err and number:
                # As a very last resort, append a micro-suffix to avoid blocking the user, still keeping order
                for i in range(1, 10):
                    suffix = f"-{i}"
                    try:
                        with self.env.cr.savepoint():
                            payment.sudo().write({
                                "x_ceci_number": f"{number}{suffix}",
                                "x_ceci_type": ctype,
                            })
                        last_err = None
                        break
                    except IntegrityError:
                        continue
                if last_err:
                    raise last_err

    def action_post(self):
        res = super().action_post()
        # Asignar después del posteo exitoso
        self._assign_ceci_number_if_needed()
        return res

    # --- Registry hook to ensure sequences are in sync on update/load ---
    def _register_hook(self):
        res = super()._register_hook()
        # Compute max existing CE and CI and bump sequences if needed
        self.env.cr.execute(
            """
            SELECT
                COALESCE(MAX(CASE WHEN x_ceci_number LIKE 'CE%%' THEN (SUBSTRING(x_ceci_number FROM '\\d+'))::int END), 0) AS max_ce,
                COALESCE(MAX(CASE WHEN x_ceci_number LIKE 'CI%%' THEN (SUBSTRING(x_ceci_number FROM '\\d+'))::int END), 0) AS max_ci
            FROM account_payment
            """
        )
        row = self.env.cr.fetchone() or (0, 0)
        max_ce, max_ci = row[0] or 0, row[1] or 0
        # Update sequences if DB has higher numbers
        seq_ce = self.env.ref("realnet_pagos_consecutivos.seq_payment_ce", raise_if_not_found=False)
        seq_ci = self.env.ref("realnet_pagos_consecutivos.seq_payment_ci", raise_if_not_found=False)
        if seq_ce and max_ce and seq_ce.number_next <= max_ce:
            seq_ce.sudo().write({"number_next": max_ce + 1})
        if seq_ci and max_ci and seq_ci.number_next <= max_ci:
            seq_ci.sudo().write({"number_next": max_ci + 1})
        return res
