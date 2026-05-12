import logging
import re

from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    tipo_servicio_id = fields.Many2one(
        "crm.service.type",
        string="Tipo de Servicio",
    )

    zona_domicilio_id = fields.Many2one(
        "crm.home.zone",
        string="Zona de Domicilio",
    )

    year_vehicule_id = fields.Many2one(
        "crm.lead.year",
        string="Año de fabricación del vehículo",
    )

    brand_id = fields.Many2one(
        "fleet.vehicle.model.brand",
        string="Marca del vehículo",
        domain="[('show_on_website', '=', True)]",
    )

    modelo_id = fields.Many2one(
        "fleet.vehicle.model",
        string="Modelo del vehículo",
        domain="[('brand_id', '=', brand_id), ('show_on_website', '=', True)]",
    )

    battery_application_id = fields.Many2one(
        "mega.battery.application",
        string="Catálogo MAC",
        domain="[('active', '=', True)]",
        help="Aplicación del catálogo MAC encontrada según la marca, modelo y año del vehículo.",
    )

    battery_option_ids = fields.Many2many(
        "mega.battery.application.option",
        string="Baterías sugeridas",
        compute="_compute_battery_option_ids",
        readonly=True,
    )

    accept_terms = fields.Boolean(
        string="Acepta términos y condiciones",
    )

    service_address = fields.Char(
        string="Dirección del servicio",
    )

    license_plate = fields.Char(
        string="Placa del vehículo",
    )

    customer_leaves_battery = fields.Boolean(
        string="¿Cliente deja batería?",
        help="Indica si el cliente deja una batería usada o de referencia.",
    )

    left_battery_reference = fields.Char(
        string="Referencia batería dejada",
        help="Referencia de la batería que deja el cliente.",
    )

    @api.depends(
        "brand_id",
        "modelo_id",
        "year_vehicule_id",
        "battery_application_id",
        "battery_application_id.option_ids",
    )
    def _compute_battery_option_ids(self):
        BatteryApplication = self.env["mega.battery.application"]

        for lead in self:
            lead.battery_option_ids = False

            if lead.battery_application_id:
                lead.battery_option_ids = lead.battery_application_id.option_ids
                continue

            if not lead.brand_id or not lead.modelo_id:
                continue

            domain = lead._get_battery_application_domain()
            applications = BatteryApplication.search(domain)

            lead.battery_option_ids = applications.mapped("option_ids")

    @api.onchange("brand_id")
    def _onchange_brand_id(self):
        for lead in self:
            lead.modelo_id = False
            lead.battery_application_id = False

        return {
            "domain": {
                "modelo_id": [
                    ("brand_id", "=", self.brand_id.id if self.brand_id else False),
                    ("show_on_website", "=", True),
                ],
                "battery_application_id": [
                    ("brand_id", "=", self.brand_id.id if self.brand_id else False),
                    ("active", "=", True),
                ],
            }
        }

    @api.onchange("modelo_id", "year_vehicule_id")
    def _onchange_vehicle_catalog_fields(self):
        for lead in self:
            lead.battery_application_id = False

            if not lead.brand_id or not lead.modelo_id:
                continue

            domain = lead._get_battery_application_domain()
            applications = self.env["mega.battery.application"].search(domain, limit=2)

            # Si solo hay una aplicación compatible, la selecciona automáticamente.
            if len(applications) == 1:
                lead.battery_application_id = applications[0]

        return {
            "domain": {
                "battery_application_id": self._get_battery_application_domain()
            }
        }

    @api.onchange("battery_application_id")
    def _onchange_battery_application_id(self):
        for lead in self:
            application = lead.battery_application_id

            if not application:
                continue

            lead.brand_id = application.brand_id
            lead.modelo_id = application.model_id

    @api.onchange("customer_leaves_battery")
    def _onchange_customer_leaves_battery(self):
        for lead in self:
            if not lead.customer_leaves_battery:
                lead.left_battery_reference = False

    @api.constrains("customer_leaves_battery", "left_battery_reference")
    def _check_left_battery_reference(self):
        for lead in self:
            if lead.customer_leaves_battery and not lead.left_battery_reference:
                raise ValidationError(_(
                    "Debe ingresar la referencia de la batería dejada por el cliente."
                ))

    def _get_battery_application_domain(self):
        self.ensure_one()

        domain = [
            ("active", "=", True),
        ]

        if self.brand_id:
            domain.append(("brand_id", "=", self.brand_id.id))

        if self.modelo_id:
            domain.append(("model_id", "=", self.modelo_id.id))

        vehicle_year = self._get_vehicle_year_value()

        if vehicle_year:
            domain += [
                "|",
                ("year_from", "=", 0),
                ("year_from", "<=", vehicle_year),
                "|",
                ("year_to", "=", 0),
                ("year_to", ">=", vehicle_year),
            ]

        return domain

    def _get_vehicle_year_value(self):
        self.ensure_one()

        year_record = self.year_vehicule_id
        if not year_record:
            return 0

        possible_values = []

        # Campos comunes donde podría estar guardado el año.
        for field_name in ("name", "year", "anio", "año", "value", "code"):
            if field_name in year_record._fields:
                possible_values.append(year_record[field_name])

        # display_name siempre existe en Odoo, aunque no haya campo name.
        possible_values.append(year_record.display_name)

        for value in possible_values:
            match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
            if match:
                return int(match.group(1))

        return 0
