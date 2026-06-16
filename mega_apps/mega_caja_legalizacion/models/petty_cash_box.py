from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PettyCashBox(models.Model):
    # Extension del encabezado real del control de efectivo.
    # Solo agrega el acumulado pendiente de legalizar sin alterar
    # la logica de saldo inicial/final ya existente.
    _inherit = "petty.cash.box"

    _LEGALIZATION_CONTROL_OPTIONS = {
        "control_efectivo",
        "control_efectivo_1a1",
        "control_efectivo_megasur",
    }

    legalization_tracking_enabled = fields.Boolean(
        string="Seguimiento de legalizacion activo",
        default=True,
        copy=False,
        readonly=True,
        help=(
            "Marca las cajas creadas desde la activacion del modulo. "
            "Las cajas anteriores conservan su flujo original."
        ),
    )
    legalization_started_at = fields.Datetime(
        string="Inicio de legalizacion",
        default=fields.Datetime.now,
        copy=False,
        readonly=True,
        help="Marca tecnica de cajas creadas con el flujo nuevo de legalizacion.",
    )
    legalization_effective = fields.Boolean(
        string="Legalizacion efectiva",
        compute="_compute_legalization_effective",
        search="_search_legalization_effective",
        help="Indica si esta caja queda dentro del corte operativo del modulo de legalizacion.",
    )
    pending_legalization_amount = fields.Monetary(
        string="Dinero no legalizado",
        currency_field="currency_id",
        compute="_compute_pending_legalization_amount",
        readonly=True,
        help=(
            "Suma de todos los egresos pendientes por legalizar del mismo "
            "control de efectivo y compañía. No afecta saldos de caja."
        ),
    )
    legalized_amount = fields.Monetary(
        string="Dinero legalizado",
        currency_field="currency_id",
        compute="_compute_legalized_amount",
        store=True,
        readonly=True,
        help="Suma acumulada de egresos marcados como legalizados en esta caja.",
    )
    pending_legalization_line_ids = fields.One2many(
        "petty.cash.box.line",
        "petty_cash_id",
        string="Pendientes por legalizar",
        domain=[
            ("petty_cash_id.legalization_effective", "=", True),
            ("move_type", "=", "out"),
            ("legalization_state", "=", "pending"),
        ],
    )
    legalized_line_ids = fields.One2many(
        "petty.cash.box.line",
        "petty_cash_id",
        string="Legalizados",
        domain=[
            ("petty_cash_id.legalization_effective", "=", True),
            ("move_type", "=", "out"),
            ("legalization_state", "=", "legalized"),
            ("legalization_archived", "=", False),
        ],
    )
    daily_movement_line_ids = fields.One2many(
        "petty.cash.box.line",
        "petty_cash_id",
        string="Movimientos",
    )

    @api.depends("legalization_tracking_enabled", "legalization_started_at")
    def _compute_legalization_effective(self):
        for record in self:
            record.legalization_effective = bool(
                record.legalization_tracking_enabled
                and record.legalization_started_at
            )

    def _search_legalization_effective(self, operator, value):
        active_domain = [
            ("legalization_tracking_enabled", "=", True),
            ("legalization_started_at", "!=", False),
        ]
        if (operator in ("=", "==") and value) or (operator == "!=" and not value):
            return active_domain
        return [
            "|",
            ("legalization_tracking_enabled", "=", False),
            ("legalization_started_at", "=", False),
        ]

    def _should_enable_legalization_from_context(self):
        option_control = (self.env.context or {}).get("option_control")
        return option_control in self._LEGALIZATION_CONTROL_OPTIONS

    @api.model
    def _cleanup_legacy_group_security_records(self):
        xmlids = [
            "mega_caja_legalizacion.menu_pending_legalization_lines_mega",
            "mega_caja_legalizacion.menu_pending_legalization_lines_1a1",
            "mega_caja_legalizacion.menu_pending_legalization_lines_megasur",
            "mega_caja_legalizacion.menu_legalized_lines_mega",
            "mega_caja_legalizacion.menu_legalized_lines_1a1",
            "mega_caja_legalizacion.menu_legalized_lines_megasur",
            "mega_caja_legalizacion.action_pending_legalization_lines_mega",
            "mega_caja_legalizacion.action_pending_legalization_lines_1a1",
            "mega_caja_legalizacion.action_pending_legalization_lines_megasur",
            "mega_caja_legalizacion.action_legalized_lines_mega",
            "mega_caja_legalizacion.action_legalized_lines_1a1",
            "mega_caja_legalizacion.action_legalized_lines_megasur",
            "mega_caja_legalizacion.group_caja_legalizacion_mega",
            "mega_caja_legalizacion.group_caja_legalizacion_1a1",
            "mega_caja_legalizacion.group_caja_legalizacion_megasur",
            "mega_caja_legalizacion.group_caja_legalizacion_manager",
        ]
        data_model = self.env["ir.model.data"].sudo()
        for xmlid in xmlids:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record:
                record.sudo().unlink()
        data_model.search([
            ("module", "=", "mega_caja_legalizacion"),
            ("name", "in", [xmlid.split(".")[1] for xmlid in xmlids]),
        ]).unlink()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._should_enable_legalization_from_context():
            res.setdefault("legalization_tracking_enabled", True)
            res.setdefault("legalization_started_at", fields.Datetime.now())
        return res

    def _compute_pending_legalization_amount(self):
        for record in self:
            if not record.legalization_effective or not record.opening_type_id:
                record.pending_legalization_amount = 0.0
                continue

            pending_lines = self.env["petty.cash.box.line"].search(
                [
                    ("petty_cash_id.legalization_effective", "=", True),
                    ("petty_cash_id.company_id", "=", record.company_id.id),
                    ("petty_cash_id.opening_type_id", "=", record.opening_type_id.id),
                    ("move_type", "=", "out"),
                    ("legalization_state", "=", "pending"),
                ]
            )
            record.pending_legalization_amount = sum(pending_lines.mapped("amount"))

    @api.depends(
        "legalization_tracking_enabled",
        "line_ids.move_type",
        "line_ids.amount",
        "line_ids.legalization_state",
    )
    def _compute_legalized_amount(self):
        for record in self:
            if not record.legalization_effective:
                record.legalized_amount = 0.0
                continue

            record.legalized_amount = sum(
                line.amount or 0.0
                for line in record.line_ids
                if line.move_type == "out" and line.legalization_state == "legalized"
            )

    @api.model_create_multi
    def create(self, vals_list):
        if self._should_enable_legalization_from_context():
            for vals in vals_list:
                vals.setdefault("legalization_tracking_enabled", True)
                vals.setdefault("legalization_started_at", fields.Datetime.now())
        return super().create(vals_list)

    def action_closed_box_cash(self):
        # Replica la logica base pero excluyendo arrastres de legalizacion
        # para que el saldo fisico no descuente el mismo egreso dos veces.
        legacy_boxes = self.filtered(lambda box: not box.legalization_effective)
        tracked_boxes = self - legacy_boxes
        result = True
        if legacy_boxes:
            result = super(PettyCashBox, legacy_boxes).action_closed_box_cash()
        if not tracked_boxes:
            return result

        for rec in tracked_boxes:
            if rec.state != "open":
                raise ValidationError(_("Solo puedes cerrar una caja en estado Abierta."))

            currency = rec.currency_id or rec.company_id.currency_id
            start = rec.opening_type_quantity or 0.0
            ingresos = sum(l.amount for l in rec.line_ids if l.move_type == "in")
            egresos = sum(l.amount for l in rec.line_ids if l.move_type == "out")
            final = currency.round(start + ingresos - egresos)

            rec.write({
                "amount_start": start,
                "amount_available": final,
                "state": "closed",
                "date_closed": fields.Datetime.now(),
            })

            if rec.opening_type_id:
                rec.opening_type_id.write({"quantity": final})

            try:
                template = self.env.ref(
                    "account_petty_cash.mail_template_petty_cash_closed",
                    raise_if_not_found=False,
                )
                primary_to = (
                    rec.user_id.partner_id.email
                    or rec.company_id.email
                    or ""
                ).strip()
                notify_group = self.env.ref(
                    "account_petty_cash.group_petty_cash_notify",
                    raise_if_not_found=False,
                )
                group_partners = (
                    notify_group and notify_group.users.mapped("partner_id")
                ) or self.env["res.partner"]
                group_partners = group_partners.filtered(lambda partner: partner.email)

                emails = set()
                if primary_to:
                    emails.add(primary_to)
                emails.update(partner.email.strip() for partner in group_partners)

                email_to = ", ".join(sorted(emails))
                email_from = (
                    rec.company_id.email
                    or self.env.user.email
                    or "no-reply@localhost"
                ).strip()

                if template and email_to:
                    email_values = {
                        "email_to": email_to,
                        "email_from": email_from,
                    }
                    template.with_context(
                        lang=rec.user_id.lang or self.env.lang,
                        email_layout_xmlid="mail.mail_notification_light",
                    ).send_mail(rec.id, force_send=True, email_values=email_values)
                else:
                    rec.message_post(
                        body=_(
                            "Caja cerrada. Inicial: %(ini)s | Ingresos: %(inn)s | Egresos: %(out)s | Final: %(fin)s"
                        )
                        % {
                            "ini": start,
                            "inn": ingresos,
                            "out": egresos,
                            "fin": final,
                        },
                        subtype_xmlid="mail.mt_comment",
                    )
            except Exception:
                pass

    @api.depends(
        "opening_type_quantity",
        "line_ids.move_type",
        "line_ids.amount",
        "state",
    )
    def _compute_resulting_balance(self):
        # Si el addon mega_petty_cash_current_balance esta instalado, su campo
        # resulting_balance reutiliza este nombre de compute.
        legacy_boxes = self.filtered(lambda box: not box.legalization_effective)
        tracked_boxes = self - legacy_boxes
        if legacy_boxes:
            super(PettyCashBox, legacy_boxes)._compute_resulting_balance()

        for rec in tracked_boxes:
            if hasattr(rec, "resulting_balance") and rec.state in ("open", "draft"):
                balance = rec.opening_type_quantity or 0.0
                for line in rec.line_ids:
                    if line.move_type == "in":
                        balance += line.amount or 0.0
                    elif line.move_type == "out":
                        balance -= line.amount or 0.0
                rec.resulting_balance = balance
