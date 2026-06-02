import random

from odoo import fields, models  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class MegaJerseyContestDraw(models.Model):
    _name = "mega.jersey.contest.draw"
    _description = "Sorteo Concurso Camiseta Selección Colombia"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(
        string="Nombre del sorteo",
        required=True,
        default="Sorteo Camiseta Selección Colombia",
        tracking=True,
    )
    draw_date = fields.Datetime(
        string="Fecha del sorteo",
        default=fields.Datetime.now,
        readonly=True,
    )
    participant_count = fields.Integer(
        string="Participantes válidos",
        compute="_compute_participant_count",
    )
    eligible_participant_count = fields.Integer(
        string="Participantes elegibles al sorteo",
        readonly=True,
    )
    winner_id = fields.Many2one(
        "mega.jersey.contest.participant",
        string="Ganador",
        readonly=True,
        tracking=True,
    )
    winner_selection_datetime = fields.Datetime(
        string="Fecha selección ganador",
        readonly=True,
    )
    winner_selection_user_id = fields.Many2one(
        "res.users",
        string="Seleccionado por",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Realizado"),
        ],
        default="draft",
        tracking=True,
    )

    winner_vat = fields.Char(
        string="Cédula ganador",
        related="winner_id.vat",
        readonly=True,
    )
    winner_phone = fields.Char(
        string="Celular ganador",
        related="winner_id.phone",
        readonly=True,
    )
    winner_email = fields.Char(
        string="Correo ganador",
        related="winner_id.email",
        readonly=True,
    )
    winner_license_plate = fields.Char(
        string="Placa ganador",
        related="winner_id.license_plate",
        readonly=True,
    )
    winner_vehicle_info = fields.Char(
        string="Marca y modelo ganador",
        related="winner_id.vehicle_info",
        readonly=True,
    )
    winner_service_acquired = fields.Selection(
        related="winner_id.service_acquired",
        string="Servicio adquirido ganador",
        readonly=True,
    )

    def _get_valid_participant_domain(self):
        return [
            ("accept_data_policy", "=", True),
            ("accept_commercial_info", "=", True),
        ]

    def _compute_participant_count(self):
        Participant = self.env["mega.jersey.contest.participant"].sudo()
        valid_count = Participant.search_count(self._get_valid_participant_domain())
        for record in self:
            record.participant_count = valid_count

    def action_select_winner(self):
        for record in self:
            if record.state == "done":
                raise UserError("Este sorteo ya fue realizado y no puede recalcularse.")

            participants = self.env["mega.jersey.contest.participant"].sudo().search(
                record._get_valid_participant_domain()
            )

            if not participants:
                raise UserError("No hay participantes válidos para realizar el sorteo.")

            winner = random.choice(participants)
            selection_datetime = fields.Datetime.now()
            eligible_count = len(participants)

            record.write(
                {
                    "winner_id": winner.id,
                    "winner_selection_datetime": selection_datetime,
                    "winner_selection_user_id": self.env.user.id,
                    "eligible_participant_count": eligible_count,
                    "draw_date": selection_datetime,
                    "state": "done",
                }
            )

            record.message_post(
                body=(
                    "Sorteo ejecutado correctamente.<br/><br/>"
                    "Ganador:<br/>"
                    f"Nombre: {winner.name}<br/>"
                    f"Cédula: {winner.vat}<br/><br/>"
                    "Fecha:<br/>"
                    f"{fields.Datetime.to_string(selection_datetime)}<br/><br/>"
                    "Usuario:<br/>"
                    f"{self.env.user.name}<br/><br/>"
                    f"Participantes elegibles: {eligible_count}<br/>"
                    f"ID ganador: {winner.id}"
                )
            )

        return {
            "effect": {
                "fadeout": "slow",
                "message": f"Ganador seleccionado: {winner.name}",
                "type": "rainbow_man",
            }
        }

    def write(self, vals):
        protected_fields = {
            "winner_id",
            "winner_selection_datetime",
            "winner_selection_user_id",
            "eligible_participant_count",
        }
        for record in self:
            if record.state == "done" and vals.get("state") and vals.get("state") != "done":
                raise UserError("No puedes devolver a borrador un sorteo realizado.")

            if protected_fields.intersection(vals):
                if record.state == "done":
                    raise UserError("No puedes modificar el resultado de un sorteo realizado.")

        return super().write(vals)

    def unlink(self):
        if any(record.state == "done" for record in self):
            raise UserError("No puedes eliminar un sorteo realizado.")
        return super().unlink()
