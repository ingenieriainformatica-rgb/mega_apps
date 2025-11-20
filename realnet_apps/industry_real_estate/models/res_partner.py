
import re
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- TUS CAMPOS ---
    is_tenant = fields.Boolean(string="Es arrendatario", default=False)
    is_property_owner = fields.Boolean(string="Es propietario",  default=False)
    
    # Partes del nombre
    x_firstname  = fields.Char(string="Primer nombre")
    x_middlename = fields.Char(string="Segundo Nombre")
    x_lastname   = fields.Char(string="Primer apellido")
    x_lastname2  = fields.Char(string="Segundo apellido")

    # --- Helpers ---
    def _compose_full_name_from_parts(self, vals):
        """Arma el nombre con prioridad a vals; si no, usa los valores actuales."""
        get = lambda k: (vals.get(k) or '').strip()
        n1 = get('x_firstname')  or (self.x_firstname  if self else '')
        n2 = get('x_middlename') or (self.x_middlename if self else '')
        a1 = get('x_lastname')   or (self.x_lastname   if self else '')
        a2 = get('x_lastname2')  or (self.x_lastname2  if self else '')
        full = " ".join(p for p in (n1, n2, a1, a2) if p)
        return full.strip()

    # Refresca name al editar partes (en formulario). Aunque name sea readonly,
    # el onchange sí puede actualizar el valor mostrado.
    @api.onchange('x_firstname', 'x_middlename', 'x_lastname', 'x_lastname2')
    def _onchange_name_parts_build_name(self):
        for rec in self:
            full = rec._compose_full_name_from_parts({})
            if full:
                rec.name = full

    # --- CREATE / WRITE MERGEADOS ---

    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context or {}
        for v in vals_list:
            # 1) Flags tenant / owner + ranks
            if v.get('is_tenant') or ctx.get('default_is_tenant'):
                v['is_tenant'] = True
                v.setdefault('customer_rank', 1)
            if v.get('is_property_owner') or ctx.get('default_is_property_owner'):
                v['is_property_owner'] = True
                v.setdefault('supplier_rank', 1)

            # 2) Si no viene name, lo componemos desde las partes
            if not v.get('name'):
                full = self._compose_full_name_from_parts(v)
                if full:
                    v['name'] = full

        return super().create(vals_list)

    def write(self, vals):
        # Guardamos primero (evitamos conflictos en constraints y onchanges)
        res = super().write(vals)

        # 1) Reforzar ranks si se activan flags por write
        for p in self:
            if vals.get('is_tenant') and p.is_tenant and p.customer_rank == 0:
                p.customer_rank = 1
            if vals.get('is_property_owner') and p.is_property_owner and p.supplier_rank == 0:
                p.supplier_rank = 1

        # 2) Si tocaron partes y NO mandaron 'name', componemos y escribimos.
        #    Solo para personas (no empresas).
        touched_parts = any(k in vals for k in ('x_firstname','x_middlename','x_lastname','x_lastname2'))
        if touched_parts and 'name' not in vals:
            for rec in self:
                if not rec.is_company:
                    full = rec._compose_full_name_from_parts(vals)
                    if full:
                        # usar super sobre el registro para evitar re-disparar tu write
                        super(ResPartner, rec).write({'name': full})

        return res


