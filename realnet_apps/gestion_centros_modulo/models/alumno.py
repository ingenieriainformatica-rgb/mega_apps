
from odoo import  _, models, fields, api
import logging

_logger = logging.getLogger(__name__)

class Student(models.Model):
    _name = 'gestion.alumno'
    _description = _('Student')  # También esto debe ser traducible
    _rec_name = 'name'

    # Basic student data
    name = fields.Char(_('Name'), required=True)
    codigo = fields.Char(_('Identification Code'))
    fecha_nacimiento = fields.Date(_('Date of Birth'))
    telefono = fields.Char(_('Phone'))
    telefono_2 = fields.Char(_('Alternate Phone'))
    email = fields.Char(_('Email'))

    # Educational-specific data
    ampa = fields.Boolean(_("Parents' Association (AMPA)"))
    actividad = fields.Char(_('Associated Activity'))
    centro_id = fields.Many2one('gestion.centro', string=_('Educational Center'))

    # Family data (as plain text, no relation to res.partner)
    nombre_padre = fields.Char(_("Father's Name"))
    nombre_madre = fields.Char(_("Mother's Name"))
    telefono_familia = fields.Char(_('Family Phone'))
