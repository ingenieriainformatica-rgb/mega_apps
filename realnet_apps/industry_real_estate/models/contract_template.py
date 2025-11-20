from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ContractTemplate(models.Model):
    _name = 'contract.template'
    _description = 'Grupo de Cláusulas de Contrato'

    name = fields.Char(string='Nombre', required=True)
    contract_title = fields.Html(string='Titulo del contrato', required=True)

    clause_line_ids = fields.Many2many(
        'clause.line',
        'contract_template_clause_rel',
        'template_id',
        'clause_id',
        string='Cláusulas del catálogo',
        domain="[('is_master', '=', True)]"
    )

    def get_vars_list(self):
        all_vars = set()

        for clause in self.clause_line_ids:
            vars_list = clause.get_vars_list()
            if isinstance(vars_list, list):
                all_vars.update(vars_list)

        # Si necesitas una lista (sin duplicados):
        all_vars_list = list(all_vars)
        return all_vars_list
    
    def _norm(self, s):
        return (s or '').strip().upper()
    
    def _prefacio_count_after(self, rec, commands):
        Line = self.env['clause.line']

        remaining_ids = set(rec.clause_line_ids.ids)
        # estado inicial de prefacios
        prefacio_ids = set(rec.clause_line_ids.filtered(
            lambda l: self._norm(l.ident) == 'PREFACIO'
        ).ids)

        for cmd in commands or []:
            op = cmd[0]
            if op == 0:  # create
                vals = cmd[2] or {}
                vid = -(len(remaining_ids) + 1)  # id virtual
                remaining_ids.add(vid)
                if self._norm(vals.get('ident')) == 'PREFACIO':
                    prefacio_ids.add(vid)

            elif op == 1:  # update existing
                line_id, vals = cmd[1], (cmd[2] or {})
                remaining_ids.add(line_id)
                if 'ident' in vals:
                    if self._norm(vals.get('ident')) == 'PREFACIO':
                        prefacio_ids.add(line_id)
                    else:
                        prefacio_ids.discard(line_id)

            elif op in (2, 3):  # unlink/delete
                line_id = cmd[1]
                remaining_ids.discard(line_id)
                prefacio_ids.discard(line_id)

            elif op == 4:  # link existing
                line_id = cmd[1]
                remaining_ids.add(line_id)
                if self._norm(Line.browse(line_id).ident) == 'PREFACIO':
                    prefacio_ids.add(line_id)

            elif op == 5:  # clear
                remaining_ids.clear()
                prefacio_ids.clear()

            elif op == 6:  # set
                new_ids = set(cmd[2] or [])
                remaining_ids = set(new_ids)
                lines = Line.browse(list(new_ids))
                prefacio_ids = set(lines.filtered(
                    lambda l: self._norm(l.ident) == 'PREFACIO'
                ).ids)

        return len(prefacio_ids)



    def write(self, vals):       
        for rec in self:
            if 'clause_line_ids' in vals:
                # validar contra el estado FINAL
                n = self._prefacio_count_after(rec, vals.get('clause_line_ids') or [])
            else:
                # sin cambios en el o2m, validar estado actual
                n = len(rec.clause_line_ids.filtered(
                    lambda l: self._norm(l.ident) == 'PREFACIO'
                ))
            if n > 1:
                raise ValidationError("Este contrato no puede tener más de un Prefacio.")
        res = super().write(vals)
        all_vars = set()

        for clause in self.clause_line_ids:
            vars_list = clause.get_vars_list()
            if isinstance(vars_list, list):
                all_vars.update(vars_list)

        # Si necesitas una lista (sin duplicados):
        # all_vars_list = list(all_vars)

        return res
    
    def add_clause_from_catalog(self, catalog_clause_id):
        """Agrega una cláusula del catálogo a esta plantilla, evitando duplicados"""
        catalog_clause = self.env['clause.line'].browse(catalog_clause_id)
        if not catalog_clause.is_master:
            raise UserError("Solo se pueden agregar cláusulas del catálogo")

        # Verificar si ya existe una cláusula en la plantilla con este master_clause_id
        existing = self.clause_line_ids.filtered(lambda c: c.master_clause_id.id == catalog_clause.id)
        if existing:
            return existing[0]  # Ya existe, no duplicar

        return ""
    
    


