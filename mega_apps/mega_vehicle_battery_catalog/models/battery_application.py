from odoo import api, fields, models, _  #type:ignore
from odoo.exceptions import ValidationError  #type:ignore


class MegaBatteryApplication(models.Model):
    _name = "mega.battery.application"
    _description = "Aplicación de batería por vehículo"
    _order = "brand_id, model_id, year_from, year_to, engine_capacity"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
        index=True,
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
        "brand_id.name",
        "model_id.name",
        "original_vehicle_name",
        "fuel_type",
        "year_from",
        "year_to",
        "engine_capacity",
        "start_stop",
    )
    def _compute_name(self):
        for rec in self:
            brand_name = rec.brand_id.name or ""
            model_name = rec._get_model_display_name()

            main_parts = [part for part in [brand_name, model_name] if part]
            main_label = " / ".join(main_parts)

            detail_parts = []

            if rec.fuel_type:
                detail_parts.append(rec.fuel_type)

            year_range = rec._get_year_range_label()
            if year_range:
                detail_parts.append(year_range)

            if rec.engine_capacity:
                detail_parts.append(rec.engine_capacity)

            if rec.start_stop:
                detail_parts.append("Start-Stop")

            detail_label = " | ".join(detail_parts)

            if main_label and detail_label:
                rec.name = f"{main_label} | {detail_label}"
            elif main_label:
                rec.name = main_label
            elif rec.original_vehicle_name:
                rec.name = rec.original_vehicle_name
            else:
                rec.name = _("Aplicación MAC")

    def _get_model_display_name(self):
        self.ensure_one()

        model_name = (self.model_id.name or "").strip()
        brand_name = (self.brand_id.name or "").strip()

        if not model_name:
            return ""

        if not brand_name:
            return model_name

        possible_prefixes = [
            f"{brand_name}/",
            f"{brand_name} /",
            f"{brand_name}-",
            f"{brand_name} -",
        ]

        for prefix in possible_prefixes:
            if model_name.lower().startswith(prefix.lower()):
                return model_name[len(prefix):].strip(" /-")

        return model_name

    def _get_year_range_label(self):
        self.ensure_one()

        if self.year_from and self.year_to:
            return f"{self.year_from}-{self.year_to}"

        if self.year_from:
            return f"Desde {self.year_from}"

        if self.year_to:
            return f"Hasta {self.year_to}"

        return ""

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
        for rec in self:
            rec.model_id = False


class MegaBatteryApplicationOption(models.Model):
    _name = "mega.battery.application.option"
    _description = "Opción de batería por aplicación"
    _order = "application_id, sequence, battery_line, option_number, reference"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
        index=True,
    )

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

    min_sale_price = fields.Monetary(
        string="Precio mínimo venta",
        currency_field="currency_id",
        help="Precio mínimo autorizado para vender esta batería.",
    )

    max_sale_price = fields.Monetary(
        string="Precio máximo venta",
        currency_field="currency_id",
        help="Precio máximo autorizado o sugerido para vender esta batería.",
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

    old_reference = fields.Char(
        string="Referencia anterior",
        index=True,
        help="Referencia anterior usada para empatar actualizaciones de precios desde archivos históricos.",
    )

    @api.depends(
        "application_id.name",
        "battery_line",
        "option_number",
        "reference",
    )
    def _compute_name(self):
        for rec in self:
            parts = []

            if rec.application_id:
                parts.append(rec.application_id.display_name)

            if rec.option_number:
                parts.append(_("Opción %s") % rec.option_number)

            line_label = rec._get_battery_line_label()
            if line_label:
                parts.append(line_label)

            if rec.reference:
                parts.append(rec.reference)

            rec.name = " | ".join(parts) if parts else _("Opción de batería")

    @api.depends("product_id")
    def _compute_product_found(self):
        for rec in self:
            rec.product_found = bool(rec.product_id)

    @api.constrains("min_sale_price", "max_sale_price")
    def _check_min_max_sale_price(self):
        for rec in self:
            if rec.min_sale_price < 0:
                raise ValidationError(
                    _("El precio mínimo de venta no puede ser negativo.")
                )

            if rec.max_sale_price < 0:
                raise ValidationError(
                    _("El precio máximo de venta no puede ser negativo.")
                )

            if (
                rec.min_sale_price
                and rec.max_sale_price
                and rec.min_sale_price > rec.max_sale_price
            ):
                raise ValidationError(
                    _("El precio mínimo de venta no puede ser mayor que el precio máximo.")
                )

    def _get_battery_line_label(self):
        self.ensure_one()

        selection = self._fields["battery_line"].selection

        if isinstance(selection, str):
            selection = getattr(self, selection)()

        elif callable(selection):
            selection = selection(self.env[self._name])

        if not selection:
            return self.battery_line or ""

        selection_map = {
            key: label
            for key, label in selection  #type:ignore
        }

        return selection_map.get(
            self.battery_line,
            self.battery_line or "",
        )
