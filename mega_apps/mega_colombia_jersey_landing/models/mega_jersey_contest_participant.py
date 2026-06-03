import re

from psycopg2 import IntegrityError  # type: ignore

from odoo import api, fields, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


DUPLICATE_VAT_MESSAGE = (
    "Usted ya está inscrito en el sorteo. "
    "Solo se permite una inscripción por cliente."
)


class MegaJerseyContestParticipant(models.Model):
    _name = "mega.jersey.contest.participant"
    _description = "Participante Concurso Camiseta Selección Colombia"
    _order = "create_date desc"
    _sql_constraints = [
        (
            "mega_jersey_contest_participant_vat_normalized_uniq",
            "unique(vat_normalized)",
            DUPLICATE_VAT_MESSAGE,
        ),
    ]

    name = fields.Char(string="Nombre completo", required=True)
    vat = fields.Char(string="Cédula", required=True)
    vat_normalized = fields.Char(
        string="Cédula normalizada",
        compute="_compute_vat_normalized",
        store=True,
        index=True,
        readonly=True,
    )
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

    @api.depends("vat")
    def _compute_vat_normalized(self):
        for record in self:
            record.vat_normalized = self._normalize_vat(record.vat)

    @api.model
    def _normalize_vat(self, vat):
        return re.sub(r"\D", "", vat or "")

    @api.model
    def _validate_vat_values(self, vals_list, existing_records=None):
        seen = {}
        existing_records = existing_records or self.browse()

        for index, vals in enumerate(vals_list):
            if "vat" not in vals:
                continue

            vat_normalized = self._normalize_vat(vals.get("vat"))
            if not vat_normalized:
                raise ValidationError("La cédula debe contener al menos un número.")

            if vat_normalized in seen:
                raise ValidationError(DUPLICATE_VAT_MESSAGE)
            seen[vat_normalized] = index

            domain = [("vat_normalized", "=", vat_normalized)]
            if existing_records:
                domain.append(("id", "not in", existing_records.ids))

            if self.sudo().search_count(domain):
                raise ValidationError(DUPLICATE_VAT_MESSAGE)

    @api.model_create_multi
    def create(self, vals_list):
        self._validate_vat_values(vals_list)
        try:
            return super().create(vals_list)
        except IntegrityError:
            self.env.cr.rollback()
            raise ValidationError(DUPLICATE_VAT_MESSAGE)

    def write(self, vals):
        if "vat" in vals:
            self._validate_vat_values([vals], existing_records=self)
        try:
            return super().write(vals)
        except IntegrityError:
            self.env.cr.rollback()
            raise ValidationError(DUPLICATE_VAT_MESSAGE)

    @api.constrains("accept_data_policy", "accept_commercial_info")
    def _check_authorizations(self):
        for record in self:
            if not record.accept_data_policy:
                raise ValidationError("Debes autorizar el tratamiento de datos personales.")
            if not record.accept_commercial_info:
                raise ValidationError("Debes autorizar el envío de información comercial.")
