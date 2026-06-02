from odoo import api, fields, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class MegaJerseyContestParticipant(models.Model):
    _name = "mega.jersey.contest.participant"
    _description = "Participante Concurso Camiseta Selección Colombia"
    _order = "create_date desc"

    name = fields.Char(string="Nombre completo", required=True)
    vat = fields.Char(string="Cédula", required=True)
    phone = fields.Char(string="Número de celular", required=True)
    email = fields.Char(string="Correo electrónico", required=True)
    street = fields.Char(string="Dirección", required=True)
    license_plate = fields.Char(string="Placa", required=True)
    vehicle_info = fields.Char(string="Marca y modelo", required=True)
    service_acquired = fields.Selection(
        [
            ("baterias", "Baterías"),
            ("llantas", "Llantas"),
            ("mega_combo", "MegaCombo"),
            ("mecanica_especializada", "Mecánica especializada"),
            ("cambio_aceite", "Cambio de aceite"),
        ],
        string="Servicio adquirido",
        required=True,
    )
    accept_data_policy = fields.Boolean(string="Autoriza tratamiento de datos", required=True)
    accept_commercial_info = fields.Boolean(string="Autoriza información comercial", required=True)
    website_id = fields.Many2one("website", string="Sitio web")
    ip_address = fields.Char(string="IP")
    user_agent = fields.Char(string="User Agent")
    state = fields.Selection(
        [
            ("new", "Nuevo"),
            ("processed", "Procesado"),
        ],
        default="new",
    )

    @api.constrains("accept_data_policy", "accept_commercial_info")
    def _check_authorizations(self):
        for record in self:
            if not record.accept_data_policy:
                raise ValidationError("Debes autorizar el tratamiento de datos personales.")
            if not record.accept_commercial_info:
                raise ValidationError("Debes autorizar el envío de información comercial.")
