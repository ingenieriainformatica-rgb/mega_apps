


from odoo import models, fields
from odoo.exceptions import UserError


def show_alert(self, utils):
    print("HI FROM SHOW ALERT")
    print(utils)

AUTOMATIZACIONES = {
    'show_alert': show_alert
}

class ClauseTask(models.Model):
    _name = 'clause.task'
    _description = 'Clause Task'

    name        = fields.Char(string='Nombre'     , required=True)
    code        = fields.Char(string='Codigo'     , required=True)

    clause_id = fields.Many2one('contract.clause', string='Cláusula', ondelete='cascade')
    
    def execute_task_from_clause(self, utils):
        func = AUTOMATIZACIONES.get(self.code)

        if func:
            func(self, utils)
        else:
            raise UserError("No se encontró una automatización para este código.")

        