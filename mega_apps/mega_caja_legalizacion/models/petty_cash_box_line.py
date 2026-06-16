import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PettyCashBoxLine(models.Model):
    # Extension de la linea real de movimientos.
    # Solo los egresos requieren seguimiento de legalizacion.
    _inherit = "petty.cash.box.line"

    legalization_origin_box_id = fields.Many2one(
        "petty.cash.box",
        string="Caja origen",
        compute="_compute_legalization_origin_box_id",
        store=True,
        readonly=True,
        help="Caja donde se genero originalmente el pendiente por legalizar.",
    )
    petty_cash_opening_type_id = fields.Many2one(
        "pc.cashbox.balance",
        string="Tipo de caja",
        related="petty_cash_id.opening_type_id",
        store=True,
        readonly=True,
    )
    control_cash_label = fields.Char(
        string="Control de efectivo",
        compute="_compute_control_cash_label",
        store=True,
        readonly=True,
    )
    petty_cash_date_open = fields.Datetime(
        string="Fecha de apertura caja",
        related="petty_cash_id.date_open",
        store=True,
        readonly=True,
    )
    odoo_document = fields.Char(
        string="Documento de Odoo",
        copy=False,
        help="Referencia interna del documento de Odoo asociado al soporte.",
    )
    requires_legalization = fields.Boolean(
        string="Requiere legalizacion",
        default=True,
        help="Indica si el movimiento necesita soporte administrativo.",
    )
    legalization_state = fields.Selection(
        selection=[
            ("pending", "No legalizado"),
            ("legalized", "Legalizado"),
        ],
        string="Estado de legalizacion",
        default="pending",
        required=True,
    )
    legalized_at = fields.Date(
        string="Fecha de legalizacion",
        readonly=True,
        copy=False,
        help="Fecha en la que el movimiento fue marcado como legalizado.",
    )
    pending_legalization_at = fields.Date(
        string="Fecha pendiente",
        readonly=True,
        copy=False,
        help="Fecha en la que el movimiento quedo pendiente por legalizar.",
    )
    legalization_archived = fields.Boolean(
        string="Legalizacion archivada",
        default=False,
        copy=False,
        help="Oculta legalizaciones antiguas de la pestaña operativa sin eliminar el historico.",
    )

    @api.depends("petty_cash_id")
    def _compute_legalization_origin_box_id(self):
        for record in self:
            record.legalization_origin_box_id = record.petty_cash_id

    @api.depends("petty_cash_opening_type_id.name")
    def _compute_control_cash_label(self):
        labels = {
            "control_efectivo": "MegaTecnicentro",
            "control_efectivo_1a1": "1a1",
            "control_efectivo_megasur": "MEGASUR",
        }
        for record in self:
            technical_name = record.petty_cash_opening_type_id.name
            record.control_cash_label = labels.get(technical_name, technical_name or "")

    @api.model
    def _clean_description_text(self, description):
        marker = "[Pendiente anterior]"
        text = description or ""
        while marker in text:
            text = text.replace(marker, "").strip()
        return " ".join(text.split())

    def _selection_label(self, field_name, value):
        field = self._fields[field_name]
        return dict(field.selection).get(value, value or "")

    def _compose_line_summary(self):
        self.ensure_one()
        move_type = self._selection_label("move_type", self.move_type)
        state = self._selection_label("legalization_state", self.legalization_state)
        partner = self.partner_id.display_name or "-"
        return _(
            "Tipo de movimiento: %(type)s | Tercero: %(partner)s | Monto: %(amount)s | Estado de legalizacion: %(state)s | Descripcion: %(description)s"
        ) % {
            "type": move_type,
            "partner": partner,
            "amount": self.amount,
            "state": state,
            "description": self.description or "-",
        }

    def _post_box_message(self, title, body):
        for record in self:
            if record.petty_cash_id:
                record.petty_cash_id.message_post(
                    body=f"{title}<br/>{body}",
                    subtype_xmlid="mail.mt_note",
                )

    def _ensure_box_open_for_real_movements(self):
        for record in self:
            box = record.petty_cash_id
            if not box or box.state != "draft":
                continue
            box.state = "open"

    def _check_legalization_permission(self):
        if not self.env.user.has_group("mega_caja_legalizacion.group_caja_legalizacion_user"):
            raise UserError(_("No tiene permisos para legalizar este control de efectivo."))

    @api.model
    def _sanitize_legalization_vals(self, vals, record=None):
        vals = dict(vals)
        current_state = record.legalization_state if record else None
        current_requires = record.requires_legalization if record else True

        legalization_state = vals.get("legalization_state", current_state)
        requires_legalization = vals.get("requires_legalization", current_requires)

        move_type = vals.get("move_type", record.move_type if record else "in")
        today = fields.Date.context_today(self)

        if "description" in vals:
            vals["description"] = self._clean_description_text(vals["description"])

        if legalization_state == "not_applicable":
            legalization_state = "legalized"

        # Solo se manejan dos estados visibles. Los ingresos quedan como
        # legalizados para evitar un tercer estado administrativo.
        if move_type == "in":
            legalization_state = "legalized"
            vals["requires_legalization"] = False
            vals["pending_legalization_at"] = False
        elif not record or ("move_type" in vals and "legalization_state" not in vals):
            # Un egreso nuevo, o una linea convertida a egreso, siempre debe
            # iniciar pendiente. La legalizacion es una accion posterior.
            legalization_state = "pending"
        else:
            vals["requires_legalization"] = True

        vals["legalization_state"] = legalization_state

        if legalization_state == "legalized":
            if move_type == "out":
                if "legalized_at" not in vals and (not record or record.legalization_state != "legalized"):
                    vals["legalized_at"] = today
                if not vals.get("pending_legalization_at") and not (record and record.pending_legalization_at):
                    vals["pending_legalization_at"] = today
            else:
                vals["pending_legalization_at"] = False
                vals["legalized_at"] = False
            vals["legalization_archived"] = False
        elif legalization_state == "pending":
            if "pending_legalization_at" not in vals and (not record or record.legalization_state != "pending"):
                vals["pending_legalization_at"] = today
            if "legalization_state" in vals or "requires_legalization" in vals:
                vals["legalized_at"] = False
                vals["legalization_archived"] = False

        return vals

    @api.model
    def _cron_archive_old_legalized_lines(self):
        today = fields.Date.context_today(self)
        first_day_current_month = today.replace(day=1)
        # El cron debe barrer legalizaciones de todas las companias, no solo
        # la compania activa del usuario que ejecuta la tarea programada.
        company_ids = self.env["res.company"].sudo().search([]).ids
        lines = self.sudo().with_context(allowed_company_ids=company_ids).search(
            [
                ("move_type", "=", "out"),
                ("legalization_state", "=", "legalized"),
                ("legalization_archived", "=", False),
                ("legalized_at", "!=", False),
                ("legalized_at", "<", first_day_current_month),
            ]
        )
        lines.write({"legalization_archived": True})
        _logger.info(
            "Archivo mensual de legalizaciones de caja: %s movimientos archivados antes de %s.",
            len(lines),
            first_day_current_month,
        )

    def action_mark_as_legalized(self):
        self._check_legalization_permission()
        today = fields.Date.context_today(self)
        self.write({
            "legalization_state": "legalized",
            "legalized_at": today,
        })
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model_create_multi
    def create(self, vals_list):
        box_ids = {vals.get("petty_cash_id") for vals in vals_list if vals.get("petty_cash_id")}
        tracked_box_ids = set(
            self.env["petty.cash.box"]
            .browse(box_ids)
            .filtered("legalization_effective")
            .ids
        )
        sanitized_vals_list = [
            self._sanitize_legalization_vals(vals)
            if vals.get("petty_cash_id") in tracked_box_ids
            else vals
            for vals in vals_list
        ]
        records = super().create(sanitized_vals_list)
        for record in records.filtered(lambda line: line.petty_cash_id.legalization_effective):
            record._ensure_box_open_for_real_movements()
            prefix = _("Se registró un nuevo movimiento en el control de efectivo")
            record._post_box_message(prefix, record._compose_line_summary())
        return records

    def write(self, vals):
        tracked_records = self.filtered(lambda line: line.petty_cash_id.legalization_effective)
        untracked_records = self - tracked_records
        result = True
        if untracked_records:
            result = super(PettyCashBoxLine, untracked_records).write(vals)
        if not tracked_records:
            return result

        snapshots = {
            record.id: {
                "move_type": record.move_type,
                "partner_name": record.partner_id.display_name or "-",
                "amount": record.amount,
                "description": record.description or "-",
                "odoo_document": record.odoo_document or "-",
                "legalization_state": record.legalization_state,
                "legalized_at": record.legalized_at,
            }
            for record in tracked_records
        }
        for record in tracked_records:
            sanitized_vals = self._sanitize_legalization_vals(vals, record=record)
            super(PettyCashBoxLine, record).write(sanitized_vals)
            record._ensure_box_open_for_real_movements()
            previous = snapshots[record.id]
            changes = []
            if previous["move_type"] != record.move_type:
                changes.append(
                    _("Tipo de movimiento: %(old)s -> %(new)s") % {
                        "old": record._selection_label("move_type", previous["move_type"]),
                        "new": record._selection_label("move_type", record.move_type),
                    }
                )
            if previous["partner_name"] != (record.partner_id.display_name or "-"):
                changes.append(
                    _("Tercero: %(old)s -> %(new)s") % {
                        "old": previous["partner_name"],
                        "new": record.partner_id.display_name or "-",
                    }
                )
            if previous["amount"] != record.amount:
                changes.append(
                    _("Monto: %(old)s -> %(new)s") % {
                        "old": previous["amount"],
                        "new": record.amount,
                    }
                )
            if previous["description"] != (record.description or "-"):
                changes.append(
                    _("Descripcion: %(old)s -> %(new)s") % {
                        "old": previous["description"],
                        "new": record.description or "-",
                    }
                )
            if previous["odoo_document"] != (record.odoo_document or "-"):
                changes.append(
                    _("Documento de Odoo: %(old)s -> %(new)s") % {
                        "old": previous["odoo_document"],
                        "new": record.odoo_document or "-",
                    }
                )
            if previous["legalization_state"] != record.legalization_state:
                changes.append(
                    _("Estado de legalizacion: %(old)s -> %(new)s") % {
                        "old": record._selection_label("legalization_state", previous["legalization_state"]),
                        "new": record._selection_label("legalization_state", record.legalization_state),
                    }
                )
            if previous["legalized_at"] != record.legalized_at:
                changes.append(
                    _("Fecha de legalizacion: %(old)s -> %(new)s") % {
                        "old": previous["legalized_at"] or "-",
                        "new": record.legalized_at or "-",
                    }
                )
            if changes:
                record._post_box_message(_("Se actualizó un movimiento del control de efectivo"), "<br/>".join(changes))
        return True

    def unlink(self):
        payload = [
            (
                record.petty_cash_id,
                _("Se eliminó un movimiento del control de efectivo"),
                record._compose_line_summary(),
            )
            for record in self
        ]
        result = super().unlink()
        for box, title, body in payload:
            if box.exists():
                box.message_post(body=f"{title}<br/>{body}", subtype_xmlid="mail.mt_note")
        return result

    @api.onchange("move_type")
    def _onchange_move_type_set_legalization(self):
        for record in self:
            values = self._sanitize_legalization_vals(
                {
                    "move_type": record.move_type,
                    "legalization_state": record.legalization_state,
                    "requires_legalization": record.requires_legalization,
                },
            )
            record.requires_legalization = values.get("requires_legalization", record.requires_legalization)
            record.legalization_state = values.get("legalization_state", record.legalization_state)
            record.legalized_at = values.get("legalized_at", record.legalized_at)
