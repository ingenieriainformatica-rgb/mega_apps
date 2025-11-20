from odoo import _, models, fields, api

class EducationalCenter(models.Model):
    _name = 'gestion.centro'
    _description = _('Educational Center')

    name = fields.Char(_('Name'), required=True)
    lugar = fields.Char(_('Location'))
    email = fields.Char(_('Email'))
    ampa_telefono = fields.Char(_("Parents' Association Phone"))

    # Computed field to display number of students
    alumno_count = fields.Integer(_('Number of Students'), compute='_compute_alumno_count')

    @api.depends()
    def _compute_alumno_count(self):
        for record in self:
            record.alumno_count = self.env['gestion.alumno'].search_count([
                ('centro_id', '=', record.id)
            ])

    def action_view_alumnos(self):
        """Action to open the student list filtered by this center"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Students of %s') % self.name,  # Traducible con parámetro
            'view_mode': 'list,form',
            'res_model': 'gestion.alumno',
            'domain': [('centro_id', '=', self.id)],
            'context': {
                'default_centro_id': self.id,
                'search_default_centro_id': self.id,
            },
            'target': 'current',
        }