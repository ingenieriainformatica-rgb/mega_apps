


from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ClauseVar(models.Model):
    _name = 'clause.var'
    _description = 'Variable de Cláusula'

    contract_id = fields.Many2one('sale.order', string='Contrato', required=True, ondelete='cascade')
    clause_id = fields.Many2one('clause.line', string='Cláusula', ondelete='cascade')
    key = fields.Char(string='Variable', required=True)
    value = fields.Char(string='Valor', default='')

    
    # modificacion anexos
    source = fields.Selection(
        [('template', 'From Template'),
         ('annex', 'From Annex'),
         ('manual', 'Manual')],
        default='template',
        required=True
    )
    annex_id = fields.Many2one('contract.annex', string='Anexo origen', ondelete='set null')

    # Compatible con Odoo 18 y 19
    try:
        # Odoo 19: Nueva sintaxis con models.Constraint
        _unique_var_per_contract_clause = models.Constraint(
            'unique(contract_id, clause_id, key)',
            'Una variable solo puede existir una vez por cláusula en cada contrato'
        )
    except AttributeError:
        # Odoo 18: Sintaxis antigua con _sql_constraints
        _sql_constraints = [
            ('unique_var_per_contract_clause',
            'unique(contract_id, clause_id, key)',
            'Una variable solo puede existir una vez por cláusula en cada contrato')
        ]


    def write(self, vals):
        updating_value = 'value' in vals
        res = super().write(vals)

        if updating_value:
            for record in self:
                related = self.env['clause.var'].sudo().search([
                    ('contract_id', '=', record.contract_id.id),
                    ('key', '=', record.key),
                    ('id', '!=', record.id)
                ])
                for r in related:
                    if r.value != vals['value']:
                        r.sudo().with_context(skip_sync=True).write({'value': vals['value']})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Validar que clause_id y contract_id sean consistentes"""
        _logger.info("clause.var.create invoked: attempting to create %s variables", len(vals_list))

        for vals in vals_list:
            if vals.get('clause_id') and vals.get('contract_id'):
                clause = self.env['clause.line'].browse(vals['clause_id'])
                if clause.sale_order_id and clause.sale_order_id.id != vals['contract_id']:
                    raise ValidationError(
                        "La cláusula debe pertenecer al mismo contrato que la variable"
                    )
        # Filtrar duplicados antes de crear
        to_create = []
        for vals in vals_list:
            contract_id = vals.get('contract_id')
            clause_id = vals.get('clause_id')
            key = vals.get('key')
            value = vals.get('value')

            _logger.debug("Processing clause.var: key=%s, value='%s', contract_id=%s, clause_id=%s", key, value, contract_id, clause_id)

            if not contract_id or not key:
                _logger.info("Skipping clause.var creation: missing contract_id or key. data=%s", vals)
                continue  # Ignora entradas incompletas (clause_id puede ser temporal)

            # Verificar si ya exista (solo para variables con clause_id)
            if clause_id:
                exists = self.search_count([
                    ('contract_id', '=', contract_id),
                    ('clause_id', '=', clause_id),
                    ('key', '=', key)
                ])
                _logger.debug("Exists with clause_id: %s", exists > 0)
            else:
                # Para variables temporales sin clause_id, verificar solo por contract_id y key
                exists = self.search_count([
                    ('contract_id', '=', contract_id),
                    ('key', '=', key),
                    ('clause_id', '=', False)
                ])
                _logger.debug("Exists without clause_id: %s", exists > 0)

            if not exists:
                to_create.append(vals)
                _logger.debug("Added to create list: %s", vals)

        result = super().create(to_create)
        return result