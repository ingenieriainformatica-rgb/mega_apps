from odoo import api, fields, models  # type: ignore


class MegaWhatsappMessageLog(models.Model):
    _name = "mega.whatsapp.message.log"
    _description = "WhatsApp message idempotency log"
    _order = "processed_at desc, id desc"

    external_message_id = fields.Char(required=True, index=True)
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        required=True,
        index=True,
    )
    phone = fields.Char(index=True)
    payload_hash = fields.Char(index=True)
    message_body = fields.Text()
    processed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    session_id = fields.Many2one("mega.whatsapp.session", ondelete="set null", index=True)
    channel_id = fields.Many2one("discuss.channel", ondelete="set null", index=True)
    mail_message_id = fields.Many2one("mail.message", ondelete="set null", index=True)

    _sql_constraints = [
        (
            "unique_external_message_direction",
            "unique(external_message_id, direction)",
            "This WhatsApp message was already processed for this direction.",
        ),
    ]

    @api.model
    def reserve_once(self, external_message_id, direction, **values):
        external_message_id = (external_message_id or "").strip()
        direction = (direction or "").strip()
        if not external_message_id or not direction:
            return self.browse(), False

        existing = self.sudo().search(
            [
                ("external_message_id", "=", external_message_id),
                ("direction", "=", direction),
            ],
            limit=1,
        )
        if existing:
            return existing, False

        create_values = {
            "external_message_id": external_message_id,
            "direction": direction,
            **values,
        }
        try:
            with self.env.cr.savepoint():
                return self.sudo().create(create_values), True
        except Exception:
            existing = self.sudo().search(
                [
                    ("external_message_id", "=", external_message_id),
                    ("direction", "=", direction),
                ],
                limit=1,
            )
            if existing:
                return existing, False
            raise
