# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class FleetRepairChecklist(models.Model):
    _name = 'fleet.repair.checklist'
    _description = "FLEET REPAIR Checklist"

    name = fields.Char('Checklist Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Char(string="Description")
    done = fields.Boolean(string="Done")

    def unlink(self):
        fleet_repair_obj = self.env['fleet.repair']
        rule_ranges = fleet_repair_obj.search([('repair_checklist_ids', 'in', self.ids)])
        if rule_ranges:
            raise UserError(
                _("You Are Trying To Delete a Record That Is Still Referenced!\nInstead Delete The Record Use Archive"))
        return super(FleetRepairChecklist, self).unlink()


class FleetRepairReceptionChecklistTemplate(models.Model):
    _name = 'fleet.repair.reception.checklist.template'
    _description = "Reception Checklist Template"
    _order = 'name'

    name = fields.Char(string="Template", required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    line_ids = fields.One2many(
        'fleet.repair.reception.checklist.template.line',
        'template_id',
        string="Items",
        copy=True,
    )


class FleetRepairReceptionChecklistTemplateLine(models.Model):
    _name = 'fleet.repair.reception.checklist.template.line'
    _description = "Reception Checklist Template Item"
    _order = 'section, sequence, id'

    section = fields.Selection(
        [
            ('general_1', 'Inspección general (columna 1)'),
            ('general_2', 'Inspección general (columna 2)'),
            ('brakes', 'Inspección de sistema de frenos'),
            ('tires', 'Inspección de llantas'),
            ('documents', 'Estado de documentos'),
        ],
        string="Sección",
        default='general_1',
        required=True,
        index=True,
        help="Define la sección del layout tipo Excel donde se muestra el ítem.",
    )
    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'fleet.repair.reception.checklist.template',
        string="Template",
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string="Item", required=True, translate=True)
    active = fields.Boolean(default=True)
    display_options = fields.Char(
        string="Opciones (texto)",
        help="Lista separada por comas con las opciones a mostrar en el portal. "
             "Por ejemplo 'Sí,No' o 'Sí,No,Foto'. Si se deja vacío se usan las "
             "opciones por defecto (Bueno / Regular / Malo / No aplica).",
    )


class FleetRepairReceptionChecklistLine(models.Model):
    _name = 'fleet.repair.reception.checklist.line'
    _description = "Reception Checklist Line"
    _order = 'checklist_type, sequence, id'

    checklist_type = fields.Selection(
        [
            ('asesor', 'Asesor'),
            ('tecnico', 'Técnico'),
        ],
        string="Tipo de checklist",
        default='asesor',
        required=True,
        index=True,
        help="Indica si esta línea pertenece al checklist rápido del asesor "
             "(Llave/Matrícula) o al checklist detallado que llena el técnico.",
    )
    sequence = fields.Integer(default=10)
    repair_id = fields.Many2one(
        'fleet.repair',
        string="Reception",
        required=True,
        ondelete='cascade',
    )
    template_id = fields.Many2one(
        'fleet.repair.reception.checklist.template',
        string="Template",
        readonly=True,
    )
    template_line_id = fields.Many2one(
        'fleet.repair.reception.checklist.template.line',
        string="Template Item",
        readonly=True,
    )
    name = fields.Char(string="Item", required=True)
    state = fields.Selection(
        [
            ('good', 'Bueno'),
            ('regular', 'Regular'),
            ('bad', 'Malo'),
            ('not_apply', 'No aplica'),
        ],
        string="Estado",
        required=True,
        default='not_apply',
    )
    observation = fields.Text(string="Observación")
    measurement_left = fields.Char(
        string="Medida IZQ / Profundidad",
        help="Para frenos: profundidad lado izquierdo. Para llantas: profundidad de la banda de rodamiento.",
    )
    measurement_right = fields.Char(
        string="Medida DER",
        help="Para frenos: profundidad lado derecho.",
    )
    position = fields.Char(
        string="Posición",
        help="Para llantas: posición (DD, DI, TD, TI).",
    )
    expiration_date = fields.Date(
        string="Fecha de vencimiento",
        help="Para documentos: fecha de vencimiento (RTM, SOAT).",
    )
    repaired = fields.Selection(
        [
            ('yes', 'Sí'),
            ('no', 'No'),
            ('pending', 'Pendiente'),
        ],
        string="Reparado",
        default='pending',
    )

    def unlink(self):
        # Cascade autorizado desde FleetRepair.unlink(): el contexto _authorized_repair_cascade
        # es establecido por código Python interno (nunca llega por RPC porque perm_unlink
        # en este modelo requiere group_checklist_technical_manager, y el llamador usa sudo()).
        if self.env.context.get('_authorized_repair_cascade'):
            return super().unlink()

        tiene_grupo = self.env.user.has_group(
            'car_repair_industry.group_checklist_technical_manager'
        )
        _logger.info(
            "[ChecklistUnlink] usuario=%s uid=%s modelo=%s env_su=%s tiene_grupo=%s ids=%s",
            self.env.user.login,
            self.env.uid,
            self._name,
            self.env.su,
            tiene_grupo,
            self.ids,
        )
        if not tiene_grupo:
            raise AccessError(
                _("No tiene permisos para eliminar ítems del checklist. "
                  "Contacte a un Administrador Checklist.")
            )
        return super().unlink()

    def get_pdf_state_label(self):
        self.ensure_one()
        opts_str = self.template_line_id.display_options if self.template_line_id else ''
        if opts_str:
            opts = [o.strip() for o in opts_str.split(',')]
            idx_map = {'good': 0, 'bad': 1, 'regular': 2, 'not_apply': 3}
            idx = idx_map.get(self.state, 3)
            if idx < len(opts):
                return opts[idx]
        return dict(self._fields['state'].selection).get(self.state, self.state or '')
