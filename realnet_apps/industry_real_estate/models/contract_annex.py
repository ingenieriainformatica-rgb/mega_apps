from odoo import models, fields, api, _

class ContractAnnex(models.Model):
    _name = 'contract.annex'
    _description = 'Anexo de Contrato (Otrosí / Transacción)'
    _order = 'sale_order_id, sequence, id'

    sale_order_id = fields.Many2one('sale.order', required=True, ondelete='cascade', index=True, string="Contrato a modificar")
    name = fields.Char(string="Título del anexo", required=True)
    annex_type = fields.Selection([
        ('otrosi', 'Otrosí'),
        ('transaccion', 'Contrato de Transacción'),
    ], required=True, string="Tipo de anexo")

    sequence = fields.Integer(default=10)
    description = fields.Text(string="Descripción / Nota legal") 

    # Reutilizamos TU MISMO modelo de líneas (cláusulas/parágrafos/prefacio)
    # Añadimos un M2O alterno en 'clause.line' para referenciar anexos.
    clause_line_ids = fields.One2many('clause.line', 'annex_id', string="Cláusulas del anexo")

    # Render del bloque del anexo usando TU _render_single_clause y las mismas variables
    def _render_annex_block(self):
        self.ensure_one()
        order = self.sale_order_id
        variables_dict = order.get_vars_dict()
        parts = []

        # Cabecera del anexo
        title = "OTROSÍ" if self.annex_type == 'otrosi' else "CONTRATO DE TRANSACCIÓN"
        base = order.name or "Contrato principal"
        desc = (self.description or "").strip()
        header = f"""<div class="o_anx">
            <p><strong>{title}</strong> respecto al {base}.</p>
            {f'<p>{desc}</p>' if desc else ''}
        </div>"""
        parts.append(header)

        # Cuerpo del anexo (cláusulas/prefacio/parágrafos análogos a las del contrato)
        for line in self.clause_line_ids.sorted('sequence'):
            html = order._render_single_clause(line, variables_dict)
            if html:
                parts.append(html)

        return " ".join(parts)
    
    def action_confirm_anex(self):
        self.ensure_one()
        self.sale_order_id.action_add_annex_clauses(self.contract_annex_ids.ids)
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.sale_order_id:
            rec.sale_order_id.message_post(
                body=_("Se creó un %s (%s) como anexo del contrato.",
                       ) % (dict(self._fields['annex_type'].selection).get(rec.annex_type), rec.name)
            )
        return rec
    
    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.sale_order_id and any(k in vals for k in ['name','annex_type','description']):
                rec.sale_order_id.message_post(
                    body=_("Se actualizó el anexo %s (%s).",) % (rec.name,
                         dict(self._fields['annex_type'].selection).get(rec.annex_type))
                )
        return res
