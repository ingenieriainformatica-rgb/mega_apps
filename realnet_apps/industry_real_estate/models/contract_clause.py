
from odoo import models, fields,api

from odoo.exceptions import UserError

from markupsafe import Markup
from lxml import html
import re



class ContractClause(models.Model):
    _name = 'contract.clause'
    _description = 'Contract Clause'

    name = fields.Char(string='Nombre descriptivo', required=True, 
                       help="Nombre descriptivo de la cláusula, no se mostrará en el contrato")
    title = fields.Char(string='Título', required=True, help="Título de la cláusula, se mostrará en el contrato")
    
    description = fields.Html(string='Texto', required=True, help="Texto de la cláusula, puede contener variables como ${var_name}")
    
    task_ids = fields.Many2many('clause.task', string='Tareas')


    def write(self, vals):
        res = super().write(vals)

        if 'description' in vals:
            for clause in self:
                errors = clause.validate_template(clause.description)
                if errors:
                    raise UserError("Se detectó un error en la declaración de una variable:\n\n" + "\n".join(errors))

                self.env['clause.var'].search([('clause_id', '=', clause.id)]).unlink()

                vars = clause.extract_vars(clause.description)
                for var in vars:
                    self.env["clause.var"].create({
                        "contract_id": False,
                        "clause_id": clause.id,
                        "key": var,
                        "value": "",
                    })

                # Buscar todos los contratos que usan esta cláusula
                sale_orders = self.env['sale.order'].search([
                    ('sale_clause_line_ids.clause_id', '=', clause.id)
                ])

                # Forzar actualización del campo renderizado
                for order in sale_orders:
                    order._compute_rendered_clauses()
                    order.write({'rendered_clauses': order.rendered_clauses})

        return res

    @api.model_create_multi
    def create(self, vals_list):
        clauses = super().create(vals_list)
        
        for clause, vals in zip(clauses, vals_list):
            if 'description' in vals:
                errors = clause.validate_template(clause.description)

                if errors:
                    raise UserError(
                        "Se detectó un error en la declaración de una variable:\n\n" + "\n".join(errors)
                    )

                vars = clause.extract_vars(clause.description)
                for var in vars:
                    self.env["clause.var"].create({
                        "contract_id": False,
                        "clause_id": clause.id,
                        "key": var,
                        "value": "",
                    })
        return clauses

    def get_vars_list(self):
        self.ensure_one()
        return self.env["clause.var"].search([
            ("clause_id", "=", self.id)]).mapped("key")


    def run_tasks(self):
        for clause in self:
            for task in clause.task_ids:
                task.execute_task_from_clause( f"{self.description}" )

    def render_template_with(self, context):
        return self.render_template(self.description, context)
    
    def render_template(self, template, context) -> str:
        # Asegura que template sea una cadena
        if not isinstance(template, str):
            template = str(template)

        # Patrón para encontrar variables ${varname}
        pattern = re.compile(r"\$\{([\w_]+)\}")

        def replacer(match):
            var_name = match.group(1).strip()
            if var_name in context:
                return str(context[var_name])
            else:
                # Si no está en el contexto, deja el marcador sin cambios y muestra aviso
                print(f"[!] Variable no encontrada en el contexto: {var_name}")
                return match.group(0)

        # Reemplaza todas las variables en template usando el contexto
        result = pattern.sub(replacer, template)
        return result
    
    def extract_vars(self, template) -> list:
        if not isinstance(template, str):
            template = str(template)

        pattern = re.compile(r"\$\{(.*?)\}")
        return [match.strip() for match in pattern.findall(template)]

    def validate_template(self, template: str) -> list:
        if not isinstance(template, str):
            template = str(template)

        errors = []

        # valid_placeholders = re.findall(r"\$\{[\w_]+\}", template)
        all_placeholders_raw = re.findall(r"\$\{.*?\}", template)

        for raw in all_placeholders_raw:
            if not re.fullmatch(r"\$\{[\w_]+\}", raw):
                errors.append(f"Marcador mal formado: {raw}")

        if re.search(r"\$\{[^\}]*$", template):
            errors.append("Marcador no cerrado: empieza con `${` pero no tiene `}`.")

        valid_spans = [m.span() for m in re.finditer(r"\$\{[\w_]+\}", template)]
        orphaned_closing_positions = []

        for match in re.finditer(r"\}", template):
            pos = match.start()
            if not any(start <= pos <= end for start, end in valid_spans):
                orphaned_closing_positions.append(pos)

        if orphaned_closing_positions:
            errors.append("Llave '}' sin apertura '${'")

        return errors