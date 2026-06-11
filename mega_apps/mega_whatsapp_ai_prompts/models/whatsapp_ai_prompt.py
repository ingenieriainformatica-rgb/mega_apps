from odoo import api, fields, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class MegaWhatsappAiPrompt(models.Model):
    _name = "mega.whatsapp.ai.prompt"
    _description = "Prompt IA WhatsApp"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    flow_type = fields.Selection(
        [
            ("simple", "Simple"),
            ("advanced", "Avanzado"),
        ],
        required=True,
        index=True,
    )
    prompt_type = fields.Selection(
        [
            ("main", "Principal"),
            ("after_hours", "Fuera de horario"),
            ("advisor_handoff", "Paso a asesor"),
            ("multimedia", "Multimedia"),
            ("coverage", "Cobertura"),
            ("fallback", "Fallback"),
        ],
        required=True,
        index=True,
    )
    prompt_text = fields.Text(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    team_id = fields.Many2one("crm.team", string="Equipo de ventas")
    start_time = fields.Float()
    end_time = fields.Float()
    weekdays = fields.Char()
    version = fields.Char()
    notes = fields.Text()
    sequence = fields.Integer(default=10)

    @api.constrains("active", "code", "flow_type", "prompt_type", "company_id", "team_id")
    def _check_unique_active_prompt_scope(self):
        for prompt in self:
            if not prompt.active:
                continue

            domain = [
                ("id", "!=", prompt.id),
                ("active", "=", True),
                ("code", "=", prompt.code),
                ("flow_type", "=", prompt.flow_type),
                ("prompt_type", "=", prompt.prompt_type),
                ("company_id", "=", prompt.company_id.id or False),
                ("team_id", "=", prompt.team_id.id or False),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    "Ya existe un prompt activo con el mismo codigo, flujo, tipo, "
                    "compania y equipo de ventas."
                )
