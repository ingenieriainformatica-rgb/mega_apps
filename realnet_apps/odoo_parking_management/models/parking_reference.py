from odoo import api, fields, models, _


class ParkingReference(models.Model):
    _name = 'parking.reference'
    _description = 'Parking Pricing Reference (Convenio)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nombre', required=True, tracking=True)
    active = fields.Boolean(string='Activo', default=True)
    is_default = fields.Boolean(string='Por defecto')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda s: s.env.company, required=True)
    site_ids = fields.Many2many('parking.site', string='Sedes aplicables', help='Si se deja vacío aplica a todas las sedes.')
    currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda', readonly=True)

    # Reglas Auto
    auto_first_minutes = fields.Integer(string='Auto: minutos del primer período', default=60, required=True)
    auto_first_source = fields.Selection(
        [('moto_product', 'Usar tarifa de producto Moto'), ('fixed_incl', 'Valor fijo (IVA incluido)')],
        string='Auto: origen precio 1er período', default='moto_product', required=True,
        help='Para Con Sello, el primer período de Auto suele cobrar al valor por hora de Moto.'
    )
    auto_first_price_incl = fields.Monetary(string='Auto: precio 1er período (IVA inc.)')

    auto_hourly_source = fields.Selection(
        [('auto_product', 'Usar tarifa de producto Auto'), ('fixed_incl', 'Valor fijo (IVA incluido)')],
        string='Auto: origen precio horas adicionales', default='auto_product', required=True
    )
    auto_hourly_price_incl = fields.Monetary(string='Auto: precio por hora adicional (IVA inc.)')

    # Reglas Moto
    moto_free_minutes = fields.Integer(string='Moto: minutos gratis', default=30, required=True)
    moto_hourly_source = fields.Selection(
        [('moto_product', 'Usar tarifa de producto Moto'), ('fixed_incl', 'Valor fijo (IVA incluido)')],
        string='Moto: origen precio por hora', default='moto_product', required=True
    )
    moto_hourly_price_incl = fields.Monetary(string='Moto: precio por hora (IVA inc.)')

    # Productos de apoyo (opcional, si no se llena se usan los productos por nombre)
    product_auto_id = fields.Many2one('product.product', string='Producto Auto', help='Servicio de parqueo Auto')
    product_moto_id = fields.Many2one('product.product', string='Producto Moto', help='Servicio de parqueo Moto')

    def _get_product(self, entry, kind):
        """kind: 'auto' or 'moto'"""
        prod = False
        if kind == 'auto':
            prod = self.product_auto_id or entry._get_parking_product('Auto')
        else:
            prod = self.product_moto_id or entry._get_parking_product('Moto')
        return prod

    def _incl_to_excl(self, product, amount_incl):
        taxes = product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
        rate = sum(t.amount for t in taxes if t.amount_type == 'percent') / 100.0 if taxes else 0.0
        return round((amount_incl or 0.0) / (1.0 + rate), 2)

    def compute_invoice_lines(self, entry, analytic_distribution=None):
        """Devuelve (invoice_lines, parking_cost_excl). Precios unitarios sin IVA.

        - Usa las reglas definidas en la referencia para la entrada dada.
        - analytic_distribution: dict opcional para setear en líneas.
        """
        self.ensure_one()
        invoice_lines = []
        cost_total = 0.0

        # Calcular minutos reales redondeando hacia arriba
        try:
            entry_dt = fields.Datetime.from_string(entry.check_in)
            out_dt = fields.Datetime.from_string(entry.check_out)
            total_minutes = int(((out_dt - entry_dt).total_seconds() + 59) // 60)
        except Exception:
            total_minutes = int(round((entry.duration or 0.0) * 60))

        veh = (entry.slot_type_id.vehicle_type or '').strip().lower()
        is_moto = 'moto' in veh

        if is_moto:
            # MOTO
            free_min = max(0, self.moto_free_minutes or 0)
            if total_minutes <= free_min:
                return [], 0.0
            # Horas a cobrar desde el minuto free_min+1
            from math import ceil
            hours_to_charge = ceil((total_minutes - free_min) / 60.0)
            product = self._get_product(entry, 'moto')
            if self.moto_hourly_source == 'moto_product' and product:
                unit_excl = product.list_price
            else:
                # Fijo IVA inc -> convertir
                prod_for_tax = product or self._get_product(entry, 'auto') or entry._get_parking_product('Auto')
                unit_excl = self._incl_to_excl(prod_for_tax, self.moto_hourly_price_incl)
            line = {
                'product_id': (product and product.id) or False,
                'name': f"Servicio Moto - {entry.name} - {entry.site_id.name} (Ref: {self.name}, {hours_to_charge} hora(s))",
                'quantity': hours_to_charge,
                'price_unit': unit_excl,
                'product_uom_id': product.uom_id.id if product else False,
            }
            if analytic_distribution:
                line['analytic_distribution'] = analytic_distribution
            invoice_lines.append((0, 0, line))
            cost_total += unit_excl * hours_to_charge
        else:
            # AUTO
            from math import ceil
            product_auto = self._get_product(entry, 'auto')
            product_moto = self._get_product(entry, 'moto')
            first_minutes = max(0, self.auto_first_minutes or 0)
            # Precio primer período
            if self.auto_first_source == 'moto_product' and product_moto:
                first_unit_excl = product_moto.list_price
            else:
                prod_for_tax = product_auto or product_moto or entry._get_parking_product('Auto')
                first_unit_excl = self._incl_to_excl(prod_for_tax, self.auto_first_price_incl)

            # Precio horas adicionales
            if self.auto_hourly_source == 'auto_product' and product_auto:
                add_unit_excl = product_auto.list_price
            else:
                prod_for_tax = product_auto or product_moto or entry._get_parking_product('Auto')
                add_unit_excl = self._incl_to_excl(prod_for_tax, self.auto_hourly_price_incl)

            if total_minutes <= first_minutes:
                line = {
                    'product_id': (product_auto and product_auto.id) or False,
                    'name': f"Servicio Auto - {entry.name} - {entry.site_id.name} (Ref: {self.name}, 0-{first_minutes} min)",
                    'quantity': 1,
                    'price_unit': first_unit_excl,
                    'product_uom_id': product_auto.uom_id.id if product_auto else False,
                }
                if analytic_distribution:
                    line['analytic_distribution'] = analytic_distribution
                invoice_lines.append((0, 0, line))
                cost_total += first_unit_excl
            else:
                add_hours = ceil((total_minutes - first_minutes) / 60.0)
                # Línea 1: primer período
                line1 = {
                    'product_id': (product_auto and product_auto.id) or False,
                    'name': f"Servicio Auto - {entry.name} - {entry.site_id.name} (Ref: {self.name}, 0-{first_minutes} min)",
                    'quantity': 1,
                    'price_unit': first_unit_excl,
                    'product_uom_id': product_auto.uom_id.id if product_auto else False,
                }
                if analytic_distribution:
                    line1['analytic_distribution'] = analytic_distribution
                invoice_lines.append((0, 0, line1))
                cost_total += first_unit_excl

                # Línea 2: adicionales
                line2 = {
                    'product_id': (product_auto and product_auto.id) or False,
                    'name': f"Servicio Auto - {entry.name} - {entry.site_id.name} (Ref: {self.name}, {add_hours} hora(s) adicionales)",
                    'quantity': add_hours,
                    'price_unit': add_unit_excl,
                    'product_uom_id': product_auto.uom_id.id if product_auto else False,
                }
                if analytic_distribution:
                    line2['analytic_distribution'] = analytic_distribution
                invoice_lines.append((0, 0, line2))
                cost_total += add_unit_excl * add_hours

        return invoice_lines, cost_total

