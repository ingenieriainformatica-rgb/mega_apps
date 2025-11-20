from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
from odoo.addons.industry_real_estate import const
import logging

_logger = logging.getLogger(__name__)

class ClauseLine(models.Model):
    _name = 'clause.line'
    _description = 'Línea de Cláusula Universal'
    _order = 'sequence, id'
        
    sequence = fields.Integer('Secuencia')
    annex_id = fields.Many2one('contract.annex', string="Anexo")
    
    ident = fields.Selection([
        ('PREFACIO',  'Prefacio'),
        ('CLAUSULA', 'Clausula'),
        ('PARAGRAFO', 'Paragrafo'),
    ], string='Prefijo')
    
    name = fields.Char(string='Nombre descriptivo', required=True, 
                    help="Nombre descriptivo de la cláusula, no se mostrará en el contrato")
    title = fields.Char(string='Título', required=True, help="Título de la cláusula, se mostrará en el contrato")
    
    description = fields.Html(string='Texto', required=True, help="Texto de la cláusula, puede contener variables como ${var_name}")

    task_ids = fields.Many2many('clause.task', string='Tareas')
    
    template_id = fields.Many2one('contract.template', string='Plantilla')
    
    sale_order_id = fields.Many2one('sale.order', string='Contrato', ondelete='cascade')
    
    # Campo para la numeración automática
    auto_number = fields.Char(
        string='Número automático',
        compute='_compute_auto_number',
        store=True,
        help="Numeración automática basada en el tipo y posición"
    )
    
    # Campo para identificar la cláusula padre (para parágrafos)
    parent_clause_line_id = fields.Many2one(
        'clause.line',
        string='Cláusula padre',
        help="Cláusula a la que pertenece este parágrafo"
    )
    
    # Jerarquía para ordenamiento
    display_order = fields.Float(
        string='Orden de visualización',
        compute='_compute_display_order',
        store=True,
    )
    
     # Campo nuevo para identificar registros "master" (catálogo)
    is_master = fields.Boolean(
        string='Es registro maestro',
        default=False,
        help="True = Registro de catálogo, False = Instancia en contrato/plantilla"
    )
    
    # Campo para referenciar al registro maestro
    master_clause_id = fields.Many2one(
        'clause.line',
        string='Cláusula maestra',
        help="Referencia al registro maestro del catálogo"
    )
    
    # Campo para validar texto renderizado
    rendered_text = fields.Html(
        compute='_compute_rendered_text',
        store=True,
    )
    # modificacion de anexos
    source = fields.Selection(
        [('template', 'From Template'),
         ('annex', 'From Annex'),
         ('manual', 'Manual')],
        default='template',
        required=True,
        help='Origen de la cláusula en el contrato.'
    )
    annex_id = fields.Many2one(
        'contract.annex',
        string='Anexo origen',
        ondelete='set null',
        help='Si esta cláusula proviene de un Anexo aislado.'
    )
    template_id = fields.Many2one(
        'contract.template',
        string='Plantilla origen',
        ondelete='set null'
    )

    # ==========================================
    # CONSTRAINTS SQL
    # ==========================================

    # Compatible con Odoo 18 y 19
    try:
        # Odoo 19: Nueva sintaxis con models.Constraint
        _context_consistency = models.Constraint(
            'CHECK((is_master = true AND sale_order_id IS NULL AND template_id IS NULL) OR '
                  '(is_master = false))',
            'El contexto de la cláusula debe ser consistente: catálogo (is_master=true) o instancia (is_master=false)'
        )
    except AttributeError:
        # Odoo 18: Sintaxis antigua con _sql_constraints
        _sql_constraints = [
            ('context_consistency',
             'CHECK((is_master = true AND sale_order_id IS NULL AND template_id IS NULL) OR '
                   '(is_master = false))',
             'El contexto de la cláusula debe ser consistente: catálogo (is_master=true) o instancia (is_master=false)'),
        ]

    # ==========================================
    # MÉTODOS COMPUTE
    # ==========================================

    @api.depends('ident', 'sequence', 'master_clause_id')
    def _compute_auto_number(self):
        """
        Calcula la numeración automática según el tipo de identificador.
        Ahora requiere que se le pase explícitamente el contrato o plantilla como contexto.
        """
        for line in self:
            if not line.exists():
                continue
            sale_order = line.sale_order_id or (self.sale_order_id if hasattr(self, 'sale_order_id') else None)
            template = line.template_id or (self.template_id if hasattr(self, 'template_id') else None)
            if line.ident == 'PREFACIO':
                # Prefacio NO lleva numeración
                line.auto_number = ''
            if line.ident == 'CLAUSULA':
                line.auto_number = line.get_clausula_number_for_context(sale_order=sale_order, template=template)
            elif line.ident == 'PARAGRAFO':
                line.auto_number = line.get_paragrafo_number_for_context(sale_order=sale_order, template=template)
            else:
                line.auto_number = ''
        

    @api.depends('sequence', 'ident', 'parent_clause_line_id')
    def _compute_display_order(self):
        """Calcula el orden de visualización jerárquico"""
        for line in self:
            if not line.exists():
                continue
            if line.ident == 'PREFACIO':
                # Siempre al inicio del preview
                line.display_order = -1.0
            if line.ident == 'CLAUSULA':
                line.display_order = line.sequence or 0
            elif line.ident == 'PARAGRAFO' and line.parent_clause_line_id:
                # Los parágrafos van después de su cláusula padre
                parent_order = line.parent_clause_line_id.sequence or 0
                line.display_order = parent_order + 0.1 + ((line.sequence or 0) * 0.01)
            else:
                line.display_order = line.sequence or 0
                
    @api.constrains('ident', 'template_id', 'sale_order_id')
    def _check_single_prefacio_per_context(self):
        for rec in self:
            if rec.ident != 'PREFACIO':
                continue

            # Solo valida cuando haya contexto explícito
            if rec.template_id:
                domain = [
                    ('ident', '=', 'PREFACIO'),
                    ('id', '!=', rec.id),
                    ('template_id', '=', rec.template_id.id),
                ]
            elif rec.sale_order_id:
                domain = [
                    ('ident', '=', 'PREFACIO'),
                    ('id', '!=', rec.id),
                    ('sale_order_id', '=', rec.sale_order_id.id),
                ]
            else:
                # SIN contexto (ni plantilla ni contrato): NO validar.
                # Evita bloquear catálogos/maestros u otros casos.
                continue
            if self.search_count(domain):
                raise ValidationError(_("Solo puede existir un Prefacio en esta plantilla/contrato."))
            
                        
    @api.constrains('ident', 'sale_order_id')
    def _check_single_preface_per_contract(self):
        for line in self:
            if not line.sale_order_id:
                continue
            if line.ident != 'preface':
                continue
            # ¿Cuántos prefacios hay en este contrato (excluyéndome si estoy editando)?
            count = self.search_count([
                ('sale_order_id', '=', line.sale_order_id.id),
                ('ident', '=', 'preface'),
                ('id', '!=', line.id),
            ])
            if count:
                raise ValidationError(
                    "Este contrato ya tiene un Prefacio. Solo se permite uno."
                )
                
    @api.depends('title', 'description', 'ident', 'parent_clause_line_id', 'sequence')
    def _compute_rendered_text(self):
        for line in self:
            if not line.exists():
                continue
            if line.sale_order_id:
                vars_dict = line.sale_order_id.get_vars_dict()
                line.rendered_text = line.sale_order_id._render_single_clause(line, vars_dict)
            else:
                line.rendered_text = ''

    # ==========================================
    # MÉTODOS HELPER PARA NUMERACIÓN
    # ==========================================

    def get_clausula_number_for_context(self, sale_order=None, template=None):
        """
        Obtiene la numeración ordinal para cláusulas en el contexto de un contrato o plantilla.
        """
        clausulas = []
        if sale_order:
            clausulas = sale_order.sale_clause_line_ids.filtered(lambda l: l.ident == 'CLAUSULA').sorted('sequence')
        elif template:
            clausulas = template.clause_line_ids.filtered(lambda l: l.ident == 'CLAUSULA').sorted('sequence')
        else:
            return ''
        try:
            clausulas_list = list(clausulas)
            if self in clausulas_list:
                position = clausulas_list.index(self) + 1
                return self._number_to_ordinal(position)
            # fallback por id si es persistido
            elif self.id and self.id in clausulas.ids:
                position = list(clausulas.ids).index(self.id) + 1
                return self._number_to_ordinal(position)
            else:
                return ''
        except Exception:
            return ''
        

    def get_paragrafo_number_for_context(self, sale_order, template=None):
        """
        Obtiene la numeración para parágrafos en el contexto de un contrato o plantilla.
        """
        if template:
            all_lines_ordered = template._organize_clause_hierarchy()
        elif sale_order:
            all_lines_ordered = sale_order._organize_clause_hierarchy()
        else:
            return ''

        paragrafo_data = next((item for item in all_lines_ordered if item['line'] == self and item['type'] == 'paragrafo'), None)
        if not paragrafo_data:
            return ''
        parent_clause = paragrafo_data['parent'] if paragrafo_data else None
        if not parent_clause:
            return ''
        paragrafos_same_parent = [
            item for item in all_lines_ordered
            if item['type'] == 'paragrafo' and item.get('parent') == parent_clause
        ]
        if len(paragrafos_same_parent) <= 1:
            return ''
        paragrafos_same_parent = sorted(paragrafos_same_parent, key=lambda x: x['line'].sequence)
        position = [item['line'] for item in paragrafos_same_parent].index(self) + 1
        return str(position)



    def _get_paragrafo_number(self, all_lines_ordered):
        """Obtiene la numeración para parágrafos"""
        
        paragrafo_data = next((item for item in all_lines_ordered if item['line'] == self and item['type'] == 'paragrafo'), None)
        # prev_lines = all_lines_ordered[:all_lines_ordered.index(self)]
        
        if not paragrafo_data:
            return ''  # Si no se encuentra el parágrafo, retornar vacío
        
        parent_clause = paragrafo_data['parent'] if paragrafo_data else None
        if not parent_clause:
            return ''
        
        paragrafos_same_parent = [
            item for item in all_lines_ordered
            if item['type'] == 'paragrafo' and item.get('parent') == parent_clause
        ]
        if len(paragrafos_same_parent) <= 1:
            return ''
        # Ordena por secuencia y calcula la posición
        paragrafos_same_parent = sorted(paragrafos_same_parent, key=lambda x: x['line'].sequence)
        position = [item['line'] for item in paragrafos_same_parent].index(self) + 1
        return str(position)
        
    
    def _number_to_ordinal(self, number):
        """Convierte número a ordinal español"""
        ordinales = {
            1: 'PRIMERA', 2: 'SEGUNDA', 3: 'TERCERA', 4: 'CUARTA', 5: 'QUINTA',
            6: 'SEXTA', 7: 'SÉPTIMA', 8: 'OCTAVA', 9: 'NOVENA', 10: 'DÉCIMA',
            11: 'UNDÉCIMA', 12: 'DUODÉCIMA', 13: 'DECIMOTERCERA', 14: 'DECIMOCUARTA', 15: 'DECIMOQUINTA',
            16: 'DECIMOSEXTA', 17: 'DECIMOSÉPTIMA', 18: 'DECIMOCTAVA', 19: 'DECIMONOVENA', 20: 'VIGÉSIMA',
            21: 'VIGÉSIMA PRIMERA', 22: 'VIGÉSIMA SEGUNDA', 23: 'VIGÉSIMA TERCERA', 24: 'VIGÉSIMA CUARTA', 25: 'VIGÉSIMA QUINTA',
            26: 'VIGÉSIMA SEXTA', 27: 'VIGÉSIMA SÉPTIMA', 28: 'VIGÉSIMA OCTAVA', 29: 'VIGÉSIMA NOVENA', 30: 'TRIGÉSIMA',
            31: 'TRIGÉSIMA PRIMERA', 32: 'TRIGÉSIMA SEGUNDA', 33: 'TRIGÉSIMA TERCERA', 34: 'TRIGÉSIMA CUARTA', 35: 'TRIGÉSIMA QUINTA',
            36: 'TRIGÉSIMA SEXTA', 37: 'TRIGÉSIMA SÉPTIMA', 38: 'TRIGÉSIMA OCTAVA', 39: 'TRIGÉSIMA NOVENA', 40: 'CUADRAGÉSIMA',
            41: 'CUADRAGÉSIMA PRIMERA', 42: 'CUADRAGÉSIMA SEGUNDA', 43: 'CUADRAGÉSIMA TERCERA', 44: 'CUADRAGÉSIMA CUARTA', 45: 'CUADRAGÉSIMA QUINTA',
            46: 'CUADRAGÉSIMA SEXTA', 47: 'CUADRAGÉSIMA SÉPTIMA', 48: 'CUADRAGÉSIMA OCTAVA', 49: 'CUADRAGÉSIMA NOVENA', 50: 'QUINQUAGÉSIMA'
        }
        return ordinales.get(number, f'{number}ª')

    # ==========================================
    # VALIDACIONES Y ONCHANGE
    # ==========================================

    @api.constrains('is_master', 'sale_order_id', 'template_id')
    def _check_context_consistency(self):
        """Validar consistencia de contexto cuando sea posible"""
        for record in self:
            # Solo validar para registros persistidos (no NewId)
            if not isinstance(record.id, models.NewId):
                if record.is_master:
                    if record.sale_order_id or record.template_id:
                        raise ValidationError(
                            f"La cláusula '{record.name}' es del catálogo (is_master=True) "
                            "pero tiene sale_order_id o template_id asignado"
                        )
                else:
                    if not (record.sale_order_id or record.template_id):
                        raise ValidationError(
                            f"La cláusula '{record.name}' es una instancia (is_master=False) "
                            "pero no tiene sale_order_id ni template_id asignado"
                        )

    @api.constrains('master_clause_id', 'name', 'title', 'description')
    def _check_clause_content(self):
        """Validar que la cláusula tenga contenido"""
        for record in self:
            # Solo validar si no es un registro maestro
            if not record.is_master:
                if not record.master_clause_id and not record.name and not record.title:
                    raise ValidationError(
                        "La cláusula debe tener contenido propio o estar basada en una cláusula del catálogo."
                    )

    @api.constrains('ident', 'master_clause_id')
    def _check_master_clause_type(self):
        """Validar que la cláusula maestra sea del mismo tipo"""
        for record in self:
            if record.master_clause_id and record.master_clause_id.ident != record.ident:
                raise ValidationError(
                    f"La cláusula maestra debe ser del mismo tipo ({record.ident})"
                )

    @api.constrains('parent_clause_line_id')
    def _check_no_circular_reference(self):
        """Evita referencias circulares en la jerarquía"""
        for line in self:
            if line.parent_clause_line_id:
                current = line.parent_clause_line_id
                visited = {line.id}
                
                while current:
                    if current.id in visited:
                        raise ValidationError(
                            "Se detectó una referencia circular en la jerarquía de cláusulas. "
                            "Una cláusula no puede ser padre de sí misma directa o indirectamente."
                        )
                    visited.add(current.id)
                    current = current.parent_clause_line_id
                    
    @api.constrains('sale_order_id', 'master_clause_id')
    def _check_no_duplicate_clauses(self):
        """Evita duplicados de cláusulas en el mismo contrato"""
        for record in self:
            if record.sale_order_id or record.master_clause_id:
                duplicate_clauses = self.env['clause.line'].search([
                    ('sale_order_id', '=', record.sale_order_id.id),
                    ('master_clause_id', '=', record.master_clause_id.id),
                    ('id', '!=', record.id)  # Excluir el registro actual
                ])
                if duplicate_clauses:
                    raise ValidationError(
                        "Se detectaron cláusulas duplicadas en el mismo contrato."
                    )

    @api.onchange('ident', 'sale_order_id', 'template_id')
    def _onchange_parent_domain(self):
        if self.ident == 'PARAGRAFO':
            # Dominio unificado: buscar en el mismo contexto
            domain = [('ident', '=', 'CLAUSULA')]
            
            if self.sale_order_id:
                # Contexto: Contrato
                domain.append(('sale_order_id', '=', self.sale_order_id.id))
            elif self.template_id:
                # Contexto: Plantilla
                domain.append(('template_id', '=', self.template_id.id))
            else:
                # Contexto: Catálogo
                domain.append(('is_master', '=', True))
            
            return {'domain': {'parent_clause_line_id': domain}}
        else:
            return {'domain': {'parent_clause_line_id': [('id', '=', False)]}}
                    
            
    def write(self, vals):
        res = super().write(vals)
        
        # for order in self._related_orders():
        #     order._sync_contract_vars_panel()
        self._sync_parent_orders_safe()

        # Si se cambia la secuencia o el ident, recomputar jerarquía
        if 'sequence' in vals or 'ident' in vals:
            for clause in self:
                if clause.sale_order_id:
                    clause.sale_order_id.recompute_paragraph_parents()

        if 'description' in vals:
            for clause in self:
                errors = clause.validate_template(clause.description)
                if errors:
                    raise UserError("Se detectó un error en la declaración de una variable:\n\n" + "\n".join(errors))

                # Solo procesar variables para cláusulas de contrato
                if clause.sale_order_id:
                    # Eliminar variables existentes de esta cláusula
                    self.env['clause.var'].search([('clause_id', '=', clause.id)]).unlink()
                    # Crear nuevas variables usando el método unificado
                    clause._extract_and_create_variables()

                # CAMBIO: Buscar contratos por master_clause_id
                if clause.is_master:
                    # Si es master, buscar instancias
                    sale_orders = self.env['sale.order'].search([
                        ('sale_clause_line_ids.master_clause_id', '=', clause.id)
                    ])
                else:
                    # Si es instancia, buscar el contrato directo
                    sale_orders = clause.sale_order_id if clause.sale_order_id else self.env['sale.order']

                # Forzar actualización del campo renderizado
                if sale_orders:
                    for order in sale_orders:
                        order._compute_rendered_clauses()

        return res
    
    def unlink(self):
        orders = self._related_orders()  # (conservar este cacheo)
        res = super().unlink()

        # 🔁 En vez de:
        # for order in orders:
        #     order._sync_contract_vars_panel()
        # ✅ Usa contexto y verificación segura:
        if not self.env.context.get('defer_sync_vars'):
            for order in orders:
                if 'contract_var_lines' in order._fields:
                    try:
                        order._sync_contract_vars_panel()
                    except Exception:
                        _logger.exception("Fallo al sincronizar panel (unlink) en SO %s", order.id)
        return res
    
    def _related_orders(self):
        """sale.order afectados por estas líneas (contrato directo o vía anexo)."""
        return (self.mapped('sale_order_id') | self.mapped('annex_id').mapped('sale_order_id')).sudo()
    
    # --- Helper centralizado para sincronización segura con el campo contract_var_lines y evitar romper---
    def _sync_parent_orders_safe(self):
        """
        Sincroniza de forma segura los sale.order relacionados.
        - Respeta el contexto 'defer_sync_vars' (cuando sale.order maneja el final del flujo).
        - Verifica que el campo 'contract_var_lines' exista en el modelo antes de invocar.
        - Agrupa por pedidos afectados usando _related_orders() (contrato directo o vía anexo).
        """
        if self.env.context.get('defer_sync_vars'):
            # SaleOrder se encargará al final (create/write con with_context)
            return

        orders = self._related_orders()
        for order in orders:
            # Evita AttributeError si la clase SO aún no inyectó el One2many
            if 'contract_var_lines' not in order._fields:
                _logger.debug("contract_var_lines aún no disponible; omito sync temprana en SO %s", order.id)
                continue
            try:
                order._sync_contract_vars_panel()
            except Exception:
                _logger.exception("Fallo al sincronizar panel (safe) en SO %s", order.id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Determinar automáticamente si es master basándose en el contexto
            if not vals.get('sale_order_id') and not vals.get('template_id'):
                # Sin contrato ni plantilla = catálogo
                vals['is_master'] = True
            else:
                # Con contrato o plantilla = instancia
                vals['is_master'] = False
            
            if vals.get('master_clause_id'):
                master = self.browse(vals['master_clause_id'])
                vals.setdefault('name', master.name or 'Sin nombre')
                vals.setdefault('title', master.title or 'Sin título')
                vals.setdefault('description', master.description or '<p>Sin contenido</p>')
            else:
                # Si no hay maestro, asegura que los campos requeridos existan
                vals.setdefault('name', 'Sin nombre')
                vals.setdefault('title', 'Sin título')
                vals.setdefault('description', '<p>Sin contenido</p>')

        clauses = super().create(vals_list)
        
        # orders = (clauses.mapped('sale_order_id') | clauses.mapped('annex_id').mapped('sale_order_id')).sudo()
        # for order in orders:
        #     order._sync_contract_vars_panel()
        
        clauses._sync_parent_orders_safe()
        
        # Recomputar jerarquía de parágrafos para contratos que tengan cláusulas nuevas
        contracts_to_update = set()
        for clause in clauses:
            if clause.sale_order_id:
                contracts_to_update.add(clause.sale_order_id)
            
            # Solo crear variables para cláusulas de contrato (no de catálogo)
            if clause.sale_order_id and clause.description:
                clause._extract_and_create_variables()
        
        # Ejecutar recomputación para todos los contratos afectados
        for contract in contracts_to_update:
            contract.recompute_paragraph_parents()
            
        return clauses

    def _extract_and_create_variables(self):
        """Extraer variables del texto y crear registros en clause.var"""
        self.ensure_one()
        
        if not self.sale_order_id:
            return  # Solo para cláusulas de contrato
            
        # Validar sintaxis antes de extraer
        errors = self.validate_template(self.description)
        if errors:
            raise UserError(
                f"Error en variables de la cláusula '{self.name}':\n" + "\n".join(errors)
            )
        
        # Extraer variables del texto
        variables = self._extract_variables_from_text(self.description)
        
        for var_name in variables:
            # Verificar si ya existe la variable para este contrato y cláusula
            existing = self.env['clause.var'].search([
                ('contract_id', '=', self.sale_order_id.id),
                ('clause_id', '=', self.id),
                ('key', '=', var_name)
            ])
            
            if not existing:
                self.env['clause.var'].create({
                    'contract_id': self.sale_order_id.id,
                    'clause_id': self.id,
                    'key': var_name,
                    'value': '',  # Usuario llenará después
                })

    def _extract_variables_from_text(self, text):
        """Extraer variables ${VAR} del texto HTML"""
        if not text:
            return []
        # Patrón mejorado: solo variables en mayúsculas con guiones bajos
        pattern = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')
        return list(set(pattern.findall(text)))

    def get_vars_list(self):
        self.ensure_one()
        
        vars = []
        
        if not self.id or isinstance(self.id, models.NewId):
            # Extraer variables del texto de la cláusula en memoria
            # Primero intentar con la descripción propia
            description_to_use = self.description
            
            # Si está vacía y tenemos master_clause_id, usar la del maestro
            if not description_to_use and self.master_clause_id:
                description_to_use = self.master_clause_id.description
            
            vars = self.extract_vars(description_to_use)
            return vars

        vars = self.env["clause.var"].search([
            ("clause_id", "=", self.id)]).mapped("key")
        
        return vars


    def run_tasks(self):
        for clause in self:
            for task in clause.task_ids:
                task.execute_task_from_clause( f"{self.description}" )

    def render_template_with(self, context):
        # Obtener el contenido efectivo
        content = self.description
        
        # Si la instancia no tiene contenido, usar el del maestro
        if not content and self.master_clause_id:
            content = self.master_clause_id.description
        
        # Si aún no hay contenido, retornar vacío
        if not content:
            return ''
        
        return self.render_template(content, context)
    
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
    
     # Método onchange para llenar automáticamente los campos
    @api.onchange('master_clause_id')
    def _onchange_master_clause_id(self):
        """Llenar automáticamente todos los campos cuando se selecciona una cláusula maestra"""
        if self.master_clause_id:
            # Copiar todos los datos de la cláusula maestra
            self.ident = self.master_clause_id.ident
            self.sequence = self.master_clause_id.sequence
            self.name = self.master_clause_id.name
            self.title = self.master_clause_id.title
            self.description = self.master_clause_id.description
        else:
            pass
        
    
    @api.constrains('ident', 'sequence', 'parent_clause_line_id', 'sale_order_id', 'template_id')
    def _check_paragrafo_not_first(self):
        """
        Valida que ningún parágrafo esté en la primera posición del contrato o plantilla
        """
        for line in self:
            if line.ident == 'PARAGRAFO':
                
                # Determinar el contexto: contrato, plantilla o catálogo
                if line.sale_order_id:
                    all_lines = line.sale_order_id.sale_clause_line_ids
                    context = f"contrato {line.sale_order_id.id}"
                elif line.template_id:
                    all_lines = line.template_id.clause_line_ids
                    context = f"plantilla {line.template_id.id}"
                elif line.is_master:
                    # En el catálogo, verificar solo si hay otras cláusulas maestras
                    all_lines = self.env['clause.line'].search([('is_master', '=', True)])
                    context = "catálogo"
                else:
                    print("  Sin contexto válido, saltando validación")
                    continue  # No validar en otros contextos
                
                # Mostrar todas las líneas antes de ordenar
                for i, l in enumerate(all_lines):
                    print(f"    Línea {i}: {l.name} (ID: {l.id}, sequence: {l.sequence}, ident: {l.ident})")

                # Ordenamiento más robusto
                try:
                    # Ordenar por secuencia, usando el índice en la lista como desempate
                    lines_with_index = [(i, l) for i, l in enumerate(all_lines)]
                    sorted_lines_with_index = sorted(lines_with_index, 
                                                   key=lambda x: (x[1].sequence or 0, x[0]))
                    sorted_lines = [l for i, l in sorted_lines_with_index]
                    
                    print(f"  Después de ordenar:")
                    for i, l in enumerate(sorted_lines):
                        print(f"    Posición {i}: {l.name} (sequence: {l.sequence}, ident: {l.ident})")
                    
                    # MEJORAR: Comparación más robusta
                    first_line = sorted_lines[0] if sorted_lines else None
                    is_first = False
                    
                    if first_line:
                        # Para registros persistidos, comparar por ID
                        if hasattr(line.id, 'origin') or hasattr(first_line.id, 'origin'):
                            # Uno o ambos son temporales, comparar por referencia
                            is_first = (line is first_line)
                        else:
                            # Ambos persistidos, comparar por ID
                            is_first = (line.id == first_line.id)
                    
                    if is_first:
                        error_msg = "Ningún parágrafo puede estar en la primera posición. Debe ir precedido de una cláusula."
                        print(f"  ERROR DETECTADO: {error_msg}")
                        raise ValidationError(error_msg)
                        
                except ValidationError:
                    # Re-lanzar ValidationError para que llegue al usuario
                    raise
                except Exception as e:
                    print(f"  ERROR TÉCNICO en validación: {e}")
                    # Solo atrapar errores técnicos, no de validación
                    
    @api.constrains('sale_order_id', 'annex_id')
    def _check_scope(self):
        for rec in self:
            # Debe pertenecer a contrato o a anexo, pero no a ambos
            if bool(rec.sale_order_id) == bool(rec.annex_id):
                raise ValidationError("Cada cláusula debe pertenecer al contrato O a un anexo (no ambos).")
            
                
    def _norm(self, s):
        return (s or '').strip().upper()

    @api.constrains('ident', 'sale_order_id', 'annex_id')
    def _check_single_prefacio_per_scope(self):
        for rec in self:
            if self._norm(rec.ident) != 'PREFACIO':
                continue

            if rec.sale_order_id:
                n = rec.sale_order_id.sale_clause_line_ids.filtered(
                    lambda l: self._norm(getattr(l, 'ident', '')) == 'PREFACIO'
                )
                if len(n) > 1:
                    raise ValidationError("El contrato no puede tener más de un PREFACIO.")

            if rec.annex_id:
                n = rec.annex_id.clause_line_ids.filtered(
                    lambda l: self._norm(getattr(l, 'ident', '')) == 'PREFACIO'
                )
                if len(n) > 1:
                    raise ValidationError("Cada anexo no puede tener más de un PREFACIO.")

