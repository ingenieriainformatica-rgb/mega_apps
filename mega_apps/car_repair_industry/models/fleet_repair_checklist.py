# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, _
from odoo.exceptions import UserError


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
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'fleet.repair.reception.checklist.template',
        string="Template",
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string="Item", required=True, translate=True)
    active = fields.Boolean(default=True)


class FleetRepairReceptionChecklistLine(models.Model):
    _name = 'fleet.repair.reception.checklist.line'
    _description = "Reception Checklist Line"
    _order = 'sequence, id'

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
    repaired = fields.Selection(
        [
            ('yes', 'Sí'),
            ('no', 'No'),
            ('pending', 'Pendiente'),
        ],
        string="Reparado",
        default='pending',
    )
