# -*- coding: utf-8 -*-
from odoo import models, fields

class ContractVar(models.Model):
    _name = 'contract.var'
    _description = 'Variable de contrato (panel)'

    name = fields.Char(required=True, index=True)   # ← tu función usa 'name'
    contract_id = fields.Many2one('sale.order', required=True, ondelete='cascade', index=True)
    value = fields.Char()  # opcional, por si quieres mostrar/editar luego
