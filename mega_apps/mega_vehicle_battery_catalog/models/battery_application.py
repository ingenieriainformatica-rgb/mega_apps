from odoo import api, fields, models, _  #type:ignore
from odoo.exceptions import ValidationError  #type:ignore


class MegaBatteryApplication(models.Model):
    _name = "mega.battery.application"
    _description = "Aplicación de batería por vehículo"
    _order = "brand_id, model_id, year_from, year_to"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
    )

    application_type = fields.Selection(
        selection=[
            ("light", "Livianos"),
            ("heavy", "Pesados"),
            ("agricultural", "Agrícola"),
            ("industrial", "Industrial / maquinaria"),
            ("other", "Otros"),
        ],
        string="Tipo de aplicación",
        required=True,
        default="light",
        index=True,
    )

    brand_id = fields.Many2one(
        comodel_name="fleet.vehicle.model.brand",
        string="Marca",
        required=True,
        index=True,
    )

    model_id = fields.Many2one(
        comodel_name="fleet.vehicle.model",
        string="Modelo / línea",
        required=True,
        index=True,
        domain="[('brand_id', '=', brand_id)]",
    )

    original_vehicle_name = fields.Char(
        string="Modelo / vehículo original MAC",
        required=True,
        index=True,
        help="Texto completo que viene en la columna MODELO / VEHÍCULO del catálogo MAC.",
    )

    fuel_type = fields.Char(
        string="Combustible",
    )

    year_from = fields.Integer(
        string="Año desde",
        index=True,
    )

    year_to = fields.Integer(
        string="Año hasta",
        index=True,
    )

    engine_capacity = fields.Char(
        string="Cilindraje",
    )

    start_stop = fields.Boolean(
        string="Start-Stop",
    )

    battery_qty = fields.Integer(
        string="Nro. baterías",
        default=1,
    )

    option_ids = fields.One2many(
        comodel_name="mega.battery.application.option",
        inverse_name="application_id",
        string="Opciones de batería",
    )

    option_count = fields.Integer(
        string="Cantidad de opciones",
        compute="_compute_option_count",
    )

    _sql_constraints = [
        (
            "battery_qty_positive",
            "CHECK(battery_qty >= 0)",
            "El número de baterías no puede ser negativo.",
        ),
    ]

    @api.depends(
        "brand_id",
        "model_id",
        "original_vehicle_name",
        "year_from",
        "year_to",
        "engine_capacity",
    )
    def _compute_name(self):
        for rec in self:
            years = ""
            if rec.year_from and rec.year_to:
                years = f" {rec.year_from}-{rec.year_to}"
            elif rec.year_from:
                years = f" desde {rec.year_from}"

            engine = f" {rec.engine_capacity}" if rec.engine_capacity else ""

            rec.name = "%s / %s%s%s" % (
                rec.brand_id.name or "",
                rec.model_id.name or "",
                years,
                engine,
            )

    @api.depends("option_ids")
    def _compute_option_count(self):
        for rec in self:
            rec.option_count = len(rec.option_ids)

    @api.constrains("year_from", "year_to")
    def _check_year_range(self):
        for rec in self:
            if rec.year_from and rec.year_to and rec.year_from > rec.year_to:
                raise ValidationError(
                    _("El año inicial no puede ser mayor que el año final.")
                )

    @api.onchange("brand_id")
    def _onchange_brand_id(self):
        self.model_id = False


class MegaBatteryApplicationOption(models.Model):
    _name = "mega.battery.application.option"
    _description = "Opción de batería por aplicación"
    _order = "application_id, sequence, battery_line, option_number"

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
    )

    application_id = fields.Many2one(
        comodel_name="mega.battery.application",
        string="Aplicación",
        required=True,
        ondelete="cascade",
        index=True,
    )

    battery_line = fields.Selection(
        selection=[
            ("mac_new", "MAC Nuevas"),
            ("mac", "MAC"),
            ("mac_12", "MAC 12 meses"),
            ("mac_gold", "Mac Gold"),
            ("mac_agm", "Mac AGM"),
            ("power_taxi", "Power Taxi"),
            ("optima", "Optima"),
            ("silver_cast", "Silver Cast"),
            ("coexito", "Coéxito"),
        ],
        string="Línea de batería",
        required=True,
        index=True,
    )

    option_number = fields.Integer(
        string="Opción",
        default=1,
    )

    reference = fields.Char(
        string="Referencia batería",
        required=True,
        index=True,
    )


    description = fields.Char(
        string="Descripción",
        help="Descripción completa de la batería según el archivo de precios.",
    )

    uom_name = fields.Char(
        string="UM",
        help="Unidad de medida del archivo de precios.",
    )

    stock_qty = fields.Float(
        string="Existencias",
        help="Existencias informativas tomadas del archivo de precios.",
    )

    average_cost = fields.Monetary(
        string="Promedio",
        currency_field="currency_id",
        help="Costo promedio según el archivo de precios.",
    )

    tax_amount = fields.Monetary(
        string="IVA",
        currency_field="currency_id",
        help="Valor de IVA según el archivo de precios.",
    )

    cost_with_tax = fields.Monetary(
        string="Costo + IVA",
        currency_field="currency_id",
        help="Costo total con IVA según el archivo de precios.",
    )

    sale_price = fields.Monetary(
        string="Precio venta",
        currency_field="currency_id",
        help="Precio de venta sugerido. En el archivo corresponde a la columna 30%.",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.template",
        string="Producto relacionado",
        domain="[('sale_ok', '=', True)]",
    )

    product_found = fields.Boolean(
        string="Producto encontrado",
        compute="_compute_product_found",
        store=True,
    )

    @api.depends("product_id")
    def _compute_product_found(self):
        for rec in self:
            rec.product_found = bool(rec.product_id)
