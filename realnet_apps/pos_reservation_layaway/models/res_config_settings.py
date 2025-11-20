from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Compatibility shim: some settings views reference this field. Define it if missing.
    replace_standard_wizard = fields.Boolean(string='Replace Standard Wizard', default=False)

    # Compat: some third-party POS settings expect this flag.
    pos_auto_select_variants = fields.Boolean(
        string="POS auto select variants",
        default=False,
        config_parameter='pos_reservation_layaway.pos_auto_select_variants'
    )

    # Compat: used by some POS variant selector add-ons
    # Removed Many2many field that could cause widget conflicts
    # pos_variant_selection_fields = fields.Many2many(
    #     'product.attribute',
    #     string='POS Variant Selection Fields',
    #     help='Atributos a usar para selección automática de variantes en POS.'
    # )

    # Compat: fallback UI behavior for variant selector
    pos_fallback_to_modal = fields.Boolean(
        string='POS Fallback to Modal',
        default=False,
        config_parameter='pos_reservation_layaway.pos_fallback_to_modal'
    )

    pos_layaway_min_percent = fields.Float(
        string="POS Layaway Min. %",
        default=20.0,
        config_parameter='pos_reservation_layaway.min_percent',
        help="Porcentaje mínimo para el abono inicial (default 20%)."
    )
    pos_layaway_expiration_days = fields.Integer(
        string="POS Layaway Días Vencimiento",
        default=90,
        config_parameter='pos_reservation_layaway.expiration_days',
        help="Plazo en días para completar el pago (default 90)."
    )
    pos_layaway_hold_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de Hold',
        help="Ubicación donde se marcan las reservas técnicas."
    )

    pos_layaway_auto_validate_picking = fields.Boolean(
        string='Validar movimiento de reserva',
        default=True,
        config_parameter='pos_reservation_layaway.auto_validate_picking',
        help='Si está activo, el traslado interno de reserva se valida automáticamente (estado Hecho).'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        location_id = params.get_param('pos_reservation_layaway.hold_location_id', default=False)
        if location_id:
            res['pos_layaway_hold_location_id'] = int(location_id)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('pos_reservation_layaway.hold_location_id', 
                        self.pos_layaway_hold_location_id.id if self.pos_layaway_hold_location_id else False)
