# -*- coding: utf-8 -*-
"""Pruebas de mega_contact_lock_identification.

Cada metodo esta numerado para poder mapearlo 1 a 1 contra la matriz de
pruebas solicitada (FASE 5 / PRUEBAS OBLIGATORIAS del encargo). Las pruebas
de "camino positivo" sobre facturas (identificacion valida => se puede
contabilizar) se verifican llamando directamente al helper
``_check_mega_commercial_identification`` en vez de completar todo el flujo
de documentos electronicos DIAN/localizacion colombiana (numeracion,
resoluciones, etc.), que es un requisito de negocio ajeno a este modulo.
Las pruebas de "camino negativo" (debe bloquear) si se ejercitan a traves de
``action_confirm``/``_post`` reales, que es el punto de integracion que nos
interesa demostrar.
"""
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMegaContactLockIdentification(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.co = cls.env.ref("base.co")
        cls.foreign_country = cls.env.ref("base.us")
        cls.cedula_type = cls.env.ref("l10n_co.national_citizen_id")
        cls.nit_type = cls.env.ref("l10n_co.rut")
        cls.correction_group = cls.env.ref(
            "mega_contact_lock_identification.group_contact_identification_correction"
        )
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.advisor = cls.env["res.partner"].search([("is_advisor", "=", True)], limit=1)

        # Este entorno ya tiene otro modulo propio (mega_fix_module_contact)
        # que exige un grupo APARTE solo para poder escribir en res.partner
        # en general. Es una capa de permisos independiente de la nuestra:
        # para que un usuario autorizado pueda de verdad completar la
        # correccion via wizard, tambien necesita ese grupo (documentado en
        # la entrega final). Se agrega aqui solo para poder probar NUESTRA
        # regla de forma aislada, sin depender de configurar ese otro modulo.
        base_edit_group = cls.env.ref(
            "mega_fix_module_contact.group_module_contact", raise_if_not_found=False
        )
        base_edit_group_ids = [base_edit_group.id] if base_edit_group else []

        # El propio usuario "por defecto" de la clase de prueba (superuser
        # tecnico, uid=1) tampoco tiene en esta copia real los grupos de
        # mega_fix_module_contact/base_partner_manager (se asignan a
        # personas concretas, no al uid tecnico). Se le otorgan aqui para
        # que las operaciones que se ejecutan sin `with_user` (p.ej. la
        # sincronizacion interna de campos comerciales que hace el nucleo
        # de Odoo al crear un hijo con parent_id) no choquen con un
        # permiso ajeno a este modulo.
        cls.env.user.sudo().write({
            "groups_id": [(4, gid) for gid in ([cls.env.ref("base.group_partner_manager").id] + base_edit_group_ids)],
        })

        # base.group_partner_manager ("Creación de contacto"): en este
        # entorno el ACL de res.partner ya esta restringido a grupos
        # concretos (no todo "Usuario interno" puede escribir contactos).
        # Se agrega para que los usuarios de prueba representen un usuario
        # de negocio realista con permiso general sobre contactos.
        base_ids = [cls.env.ref("base.group_user").id, cls.env.ref("base.group_partner_manager").id]

        cls.normal_user = cls.env["res.users"].create({
            "name": "Mega Test - Usuario Normal",
            "login": "mega_test_normal_user",
            "email": "mega_test_normal_user@example.com",
            "groups_id": [(6, 0, base_ids + base_edit_group_ids)],
        })
        cls.authorized_user = cls.env["res.users"].create({
            "name": "Mega Test - Usuario Autorizado",
            "login": "mega_test_authorized_user",
            "email": "mega_test_authorized_user@example.com",
            "groups_id": [(6, 0, base_ids + [cls.correction_group.id] + base_edit_group_ids)],
        })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _make_co_person(self, name="Persona CO Test", vat="1234567890", with_id=True):
        vals = {"name": name, "is_company": False, "country_id": self.co.id}
        if with_id:
            vals["l10n_latam_identification_type_id"] = self.cedula_type.id
            vals["vat"] = vat
        # no_vat_validation: los NIT/cedulas de prueba no traen digito de
        # verificacion real; eso lo valida l10n_co/base_vat, que es una
        # regla ortogonal a la que este modulo protege.
        return self.env["res.partner"].with_context(no_vat_validation=True).create(vals)

    def _make_co_company(self, name="Empresa CO Test", vat="900123456", with_id=True):
        vals = {"name": name, "is_company": True, "country_id": self.co.id}
        if with_id:
            vals["l10n_latam_identification_type_id"] = self.nit_type.id
            vals["vat"] = vat
        return self.env["res.partner"].with_context(no_vat_validation=True).create(vals)

    def _make_order(self, partner):
        # warehouse_id/advisor_id: exigidos por otros modulos propios de
        # este entorno (mega_sale_warehouse_move, mega_sale_advisor), ajenos
        # a lo que este modulo protege.
        return self.env["sale.order"].create({
            "partner_id": partner.id,
            "warehouse_id": self.warehouse.id,
            "advisor_id": self.advisor.id,
        })

    def _give_history(self, partner):
        """Le da 'historial comercial' minimo a un partner: una factura
        contabilizada a su nombre."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {
                "name": "Servicio de prueba",
                "quantity": 1,
                "price_unit": 100,
            })],
        })
        # Se fuerza el estado directamente (en vez de pasar por _post()) para
        # no depender de requisitos de localizacion (secuencias DIAN, tipos
        # de documento, etc.) que son ortogonales a lo que este modulo
        # protege: solo necesitamos que el partner "tenga historial".
        move.sudo().write({"state": "posted"})
        return move

    # ------------------------------------------------------------------
    # 1-6: los flujos estandar de creacion NO deben verse afectados
    # ------------------------------------------------------------------

    def test_01_crm_lead_partner_sin_vat(self):
        lead = self.env["crm.lead"].create({"name": "Oportunidad de prueba", "contact_name": "Prospecto sin ID"})
        partner = self.env["res.partner"].create({"name": "Prospecto CRM", "is_company": False})
        lead.partner_id = partner
        self.assertFalse(partner.vat)

    def test_02_website_contact_sin_vat(self):
        # Simula la creacion minima que hace un formulario web/portal (los
        # controladores de website/portal crean el partner con sudo(), ya
        # que un visitante anonimo no tiene usuario interno propio).
        partner = self.env["res.partner"].sudo().create({
            "name": "Contacto Web",
            "email": "web@example.com",
        })
        self.assertFalse(partner.vat)

    def test_03_usuario_sin_vat_en_su_partner(self):
        user = self.env["res.users"].create({
            "name": "Mega Test - Sin VAT",
            "login": "mega_test_user_sin_vat",
            "email": "mega_test_user_sin_vat@example.com",
        })
        self.assertFalse(user.partner_id.vat)

    def test_04_empleado_sin_vat_en_work_contact(self):
        if "hr.employee" not in self.env:
            self.skipTest("hr no instalado")
        employee = self.env["hr.employee"].create({"name": "Empleado de prueba"})
        # No debe lanzar ninguna excepcion de este modulo al crearse.
        self.assertTrue(employee.id)

    def test_05_name_create_sin_vat(self):
        partner_id, _name = self.env["res.partner"].name_create("Cliente rapido")
        partner = self.env["res.partner"].browse(partner_id)
        self.assertFalse(partner.vat)

    def test_06_importacion_sin_vat(self):
        # `load()` es el metodo que usa el asistente de importacion.
        result = self.env["res.partner"].load(
            ["name", "is_company"],
            [["Importado 1", "0"], ["Importado 2", "0"]],
        )
        self.assertFalse(result.get("messages"))

    # ------------------------------------------------------------------
    # 7-13: reglas de identificacion (helper directo)
    # ------------------------------------------------------------------

    def test_07_persona_colombiana_con_cedula_es_valida(self):
        partner = self._make_co_person()
        partner._check_mega_commercial_identification("la prueba")  # no debe lanzar

    def test_08_empresa_colombiana_con_nit_es_valida(self):
        partner = self._make_co_company()
        partner._check_mega_commercial_identification("la prueba")  # no debe lanzar

    def test_09_persona_colombiana_sin_vat_confirma_venta(self):
        partner = self._make_co_person(with_id=False)
        order = self._make_order(partner)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_10_empresa_colombiana_sin_nit_confirma_venta(self):
        partner = self._make_co_company(with_id=False)
        order = self._make_order(partner)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_11_contacto_extranjero_no_exige_id_colombiana(self):
        partner = self.env["res.partner"].create({
            "name": "Foreign Co", "is_company": True, "country_id": self.foreign_country.id,
        })
        order = self._make_order(partner)
        order.action_confirm()  # no debe lanzar
        self.assertEqual(order.state, "sale")

    def test_12_contacto_sin_country_id(self):
        partner = self.env["res.partner"].create({"name": "Sin Pais", "is_company": False})
        order = self._make_order(partner)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_13_contacto_hijo_no_exige_vat_propio(self):
        parent = self._make_co_company()
        # Nota: la creacion normal por ORM dispara la sincronizacion
        # estandar de Odoo del vat del padre hacia el hijo
        # (res.partner._commercial_sync_from_company). En este entorno,
        # OTRO modulo propio ajeno a este (mega_fix_module_contact)
        # interpreta ese vat recien sincronizado como "duplicado" del
        # propio padre y lo bloquea: es un bug pre-existente e
        # independiente de mega_contact_lock_identification (documentado
        # en la entrega final), que no se debe corregir aqui. Se neutraliza
        # solo en memoria, solo para esta prueba, para poder aislar la
        # regla que SI es responsabilidad de este modulo.
        with patch(
            "odoo.addons.mega_fix_module_contact.models.res_partner_fix.ResPartner._find_duplicate_vat",
            return_value=self.env["res.partner"].browse(),
        ):
            child = self.env["res.partner"].with_context(no_vat_validation=True).create({
                "name": "Sucursal Norte", "parent_id": parent.id, "type": "delivery",
            })
        order = self._make_order(child)
        order.action_confirm()  # usa commercial_partner_id (el padre, con NIT)
        self.assertEqual(order.state, "sale")

    # ------------------------------------------------------------------
    # 14: confirmacion en lote
    # ------------------------------------------------------------------

    def test_14_confirmacion_lote_no_confirma_parcialmente(self):
        good_partner = self._make_co_company(name="Empresa OK")
        bad_partner = self._make_co_person(name="Persona Incompleta", with_id=False)
        order_ok = self._make_order(good_partner)
        order_bad = self._make_order(bad_partner)

        with self.assertRaises(UserError):
            (order_ok | order_bad).action_confirm()

        self.assertEqual(order_ok.state, "draft", "no debe quedar nada confirmado si falla uno del lote")
        self.assertEqual(order_bad.state, "draft")

    # ------------------------------------------------------------------
    # 15-19: contabilizacion
    # ------------------------------------------------------------------

    def _make_invoice(self, partner, move_type="out_invoice"):
        return self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {
                "name": "Servicio de prueba", "quantity": 1, "price_unit": 100,
            })],
        })

    def test_15_factura_cliente_sin_identificacion(self):
        partner = self._make_co_person(with_id=False)
        move = self._make_invoice(partner, "out_invoice")
        with self.assertRaises(UserError):
            move._post()

    def test_16_nota_credito_cliente_sin_identificacion(self):
        partner = self._make_co_person(with_id=False)
        move = self._make_invoice(partner, "out_refund")
        with self.assertRaises(UserError):
            move._post()

    def test_17_factura_proveedor_sin_identificacion(self):
        partner = self._make_co_company(with_id=False)
        move = self._make_invoice(partner, "in_invoice")
        with self.assertRaises(UserError):
            move._post()

    def test_18_nota_credito_proveedor_sin_identificacion(self):
        partner = self._make_co_company(with_id=False)
        move = self._make_invoice(partner, "in_refund")
        with self.assertRaises(UserError):
            move._post()

    def test_19_asiento_general_sin_tercero_no_se_valida(self):
        journal = self.env["account.journal"].search([("type", "=", "general")], limit=1)
        # Se evitan cuentas de tipo receivable/payable: suelen exigir un
        # partner para conciliar, lo cual es ortogonal a esta prueba.
        safe_domain = [
            ("deprecated", "=", False),
            ("account_type", "not in", ("asset_receivable", "liability_payable")),
        ]
        account_1 = self.env["account.account"].search(safe_domain, limit=1)
        account_2 = self.env["account.account"].search(
            safe_domain + [("id", "!=", account_1.id)], limit=1,
        )
        move = self.env["account.move"].create({
            "move_type": "entry",
            "journal_id": journal.id,
            "line_ids": [
                (0, 0, {"account_id": account_1.id, "debit": 10.0, "credit": 0.0}),
                (0, 0, {"account_id": account_2.id, "debit": 0.0, "credit": 10.0}),
            ],
        })
        move._post()  # no debe exigir identificacion: move_type == 'entry'
        self.assertEqual(move.state, "posted")

    # ------------------------------------------------------------------
    # 20-21: historico
    # ------------------------------------------------------------------
    # Nota: la verificacion de que las 48 facturas historicas reales
    # permanecen intactas se hace por auditoria SQL de solo lectura sobre la
    # copia de trabajo (FASE 6), no aqui, porque ese es un hecho sobre datos
    # reales y no algo que se pueda "crear" en una prueba aislada.

    def test_21_recontabilizacion_historica_exige_identificacion(self):
        partner = self._make_co_person(with_id=False)
        move = self._make_invoice(partner, "out_invoice")
        # Se fuerza el estado a posted para simular una factura historica
        # ya contabilizada ANTES de que existiera esta validacion.
        move.sudo().write({"state": "posted"})
        move.button_draft()
        with self.assertRaises(UserError):
            move._post()

    # ------------------------------------------------------------------
    # 22-25: cambios directos de vat/tipo
    # ------------------------------------------------------------------

    def test_22_cambio_directo_vat_sin_historial(self):
        partner = self._make_co_person()
        partner.with_user(self.authorized_user).write({"vat": "9999999999"})  # no debe lanzar
        self.assertEqual(partner.vat, "9999999999")

    def test_23_cambio_directo_vat_con_historial(self):
        partner = self._make_co_person()
        self._give_history(partner)
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).write({"vat": "1112223334"})

    def test_24_borrado_vat_con_historial(self):
        partner = self._make_co_person()
        self._give_history(partner)
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).write({"vat": False})

    def test_25_cambio_tipo_con_historial(self):
        partner = self._make_co_person()
        self._give_history(partner)
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).write({
                "l10n_latam_identification_type_id": self.nit_type.id,
            })

    # ------------------------------------------------------------------
    # 26-30: usuarios/RPC/import
    # ------------------------------------------------------------------

    def test_26_usuario_normal_no_puede_modificar(self):
        partner = self._make_co_person()
        self._give_history(partner)
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).write({"vat": "1112223334"})

    def test_27_usuario_autorizado_via_wizard(self):
        partner = self._make_co_person()
        self._give_history(partner)
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": "1112223334",
            "reason": "Corrección de digitación del NIT original.",
        })
        wizard.with_user(self.authorized_user).action_confirm()
        self.assertEqual(partner.vat, "1112223334")

    def test_27b_usuario_sin_grupo_no_puede_ni_abrir_el_asistente(self):
        partner = self._make_co_person()
        self._give_history(partner)
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).action_open_mega_identification_correction()
        # Tampoco puede crear el registro del asistente directamente (ACL).
        with self.assertRaises(AccessError):
            self.env["mega.contact.identification.correction"].with_user(self.normal_user).create({
                "partner_id": partner.id,
            })

    def test_28_usuario_autorizado_intenta_write_directo(self):
        partner = self._make_co_person()
        self._give_history(partner)
        # Tiene el grupo, pero no paso por el asistente: debe seguir bloqueado.
        with self.assertRaises(UserError):
            partner.with_user(self.authorized_user).write({"vat": "1112223334"})

    def test_29_rpc_con_contexto_falsificado(self):
        partner = self._make_co_person()
        self._give_history(partner)
        other_partner = self._make_co_person(name="Otro contacto", vat="5556667778")
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": other_partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": "5556667778",
            "reason": "Motivo valido para otro contacto.",
        })
        # Usuario normal intenta reutilizar (falsificar) el context de un
        # wizard ajeno, sobre un partner distinto al del wizard.
        with self.assertRaises(UserError):
            partner.with_user(self.normal_user).with_context(
                mega_identification_correction_wizard_id=wizard.id,
            ).write({"vat": "1112223334"})

    def test_30_importacion_sobre_contacto_con_historial(self):
        partner = self._make_co_person()
        self._give_history(partner)
        original_vat = partner.vat
        # ".id" (con punto) le indica a load() que use la clave primaria
        # real de la base de datos, en vez de tratarlo como external id.
        result = self.env["res.partner"].with_user(self.normal_user).load(
            [".id", "vat"], [[str(partner.id), "1112223334"]],
        )
        self.assertTrue(result.get("messages"), "la importacion debe reportar el bloqueo, no aplicarlo en silencio")
        self.assertEqual(partner.vat, original_vat, "el vat no debe cambiar si la importacion fue bloqueada")

    # ------------------------------------------------------------------
    # 31-33: contactos tecnicos (usuario / empleado / compania)
    # ------------------------------------------------------------------

    def test_31_contacto_vinculado_a_usuario_tiene_historial(self):
        partner = self._make_co_person()
        self.env["res.users"].create({
            "name": "Usuario vinculado", "login": "mega_test_linked_user",
            "email": "mega_test_linked_user@example.com", "partner_id": partner.id,
        })
        self.assertTrue(partner._mega_has_commercial_history())

    def test_32_contacto_vinculado_a_empleado_tiene_historial(self):
        if "hr.employee" not in self.env:
            self.skipTest("hr no instalado")
        partner = self._make_co_person()
        self.env["hr.employee"].create({"name": "Empleado vinculado", "work_contact_id": partner.id})
        self.assertTrue(partner._mega_has_commercial_history())

    def test_33_contacto_de_la_compania_bloqueado_en_wizard(self):
        company_partner = self.env.company.partner_id
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": company_partner.id,
            "new_identification_type_id": self.nit_type.id,
            "new_vat": "999999999",
            "reason": "Intento sobre el partner de la compañía.",
        })
        with self.assertRaises(UserError):
            wizard.with_user(self.authorized_user).action_confirm()

    # ------------------------------------------------------------------
    # 34-36: wizard - motivo, chatter, escritura multiple
    # ------------------------------------------------------------------

    def test_34_motivo_vacio_o_solo_espacios(self):
        partner = self._make_co_person()
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": "1112223334",
            "reason": "   ",
        })
        with self.assertRaises(UserError):
            wizard.with_user(self.authorized_user).action_confirm()

    def test_35_chatter_registra_trazabilidad(self):
        partner = self._make_co_person(vat="1112223330")
        self._give_history(partner)
        old_vat = partner.vat
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": "1112223334",
            "reason": "Se corrige digito transpuesto por error de digitación.",
        })
        wizard.with_user(self.authorized_user).action_confirm()
        last_message = partner.message_ids.sorted("id", reverse=True)[0]
        self.assertIn(old_vat, last_message.body)
        self.assertIn("1112223334", last_message.body)
        self.assertIn(self.authorized_user.name, last_message.body)

    def test_36_escritura_multiple_recordset(self):
        p1 = self._make_co_person(name="Multi 1", vat="1112223330")
        p2 = self._make_co_person(name="Multi 2", vat="1112223331")
        (p1 | p2).write({"vat": "1112223334"})  # ninguno tiene historial: debe permitirse
        self.assertEqual(p1.vat, "1112223334")
        self.assertEqual(p2.vat, "1112223334")

        p3 = self._make_co_person(name="Multi 3", vat="1112223332")
        self._give_history(p3)
        with self.assertRaises(UserError):
            (p1 | p3).with_user(self.normal_user).write({"vat": "2223334445"})

    # ------------------------------------------------------------------
    # 37: compatibilidad con l10n_co_dian
    # ------------------------------------------------------------------

    def test_37_correccion_no_dispara_refresh_dian(self):
        partner = self._make_co_person(vat="1112223330")
        self._give_history(partner)
        move = self._make_invoice(partner, "out_invoice")
        move.sudo().write({"state": "posted"})
        dian_state_before = move.l10n_co_dian_state if "l10n_co_dian_state" in move._fields else None

        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": "1112223334",
            "reason": "Prueba de no interaccion con DIAN.",
        })
        wizard.with_user(self.authorized_user).action_confirm()

        if "l10n_co_dian_state" in move._fields:
            self.assertEqual(move.l10n_co_dian_state, dian_state_before,
                              "la correccion no debe alterar el estado DIAN de facturas existentes")

    # ------------------------------------------------------------------
    # 38: interaccion con mega_partner_merge_by_vat (sin depender de el)
    # ------------------------------------------------------------------

    def test_38_propuesta_de_fusion_pendiente_si_modulo_disponible(self):
        if "partner.merge.proposal" not in self.env or "partner.merge.proposal.line" not in self.env:
            self.skipTest("mega_partner_merge_by_vat no esta instalado en este entorno")

        partner = self._make_co_person()
        proposal = self.env["partner.merge.proposal"].create({
            "phase": "vat",
            "vat_key": partner.vat,
            "state": "pending",
        })
        self.env["partner.merge.proposal.line"].create({
            "proposal_id": proposal.id,
            "partner_id": partner.id,
            "original_partner_id": partner.id,
            "role": "destination",
        })
        wizard = self.env["mega.contact.identification.correction"].with_user(self.authorized_user).create({
            "partner_id": partner.id,
            "new_identification_type_id": self.cedula_type.id,
            "new_vat": partner.vat,
            "reason": "Solo se abre el asistente para revisar la advertencia.",
        })
        self.assertTrue(wizard.merge_warning, "debe advertir sobre la propuesta de fusion pendiente")

    # ------------------------------------------------------------------
    # 39: regresion - alternar Empresa/Persona debe corregir el tipo,
    # no solo asignarlo la primera vez.
    # ------------------------------------------------------------------

    def test_39_onchange_alternar_empresa_persona_corrige_tipo(self):
        # Sin `with`: no se llama a Form.save() (name/vat quedarian
        # incompletos a proposito). Solo interesa el efecto del onchange
        # sobre l10n_latam_identification_type_id.
        f = Form(self.env["res.partner"])
        f.company_type = "company"
        self.assertEqual(f.l10n_latam_identification_type_id, self.nit_type, "Empresa debe quedar en NIT")

        f.company_type = "person"
        self.assertEqual(
            f.l10n_latam_identification_type_id, self.cedula_type,
            "Persona debe quedar en Cédula de ciudadanía, no debe conservar el NIT anterior",
        )

        f.company_type = "company"
        self.assertEqual(
            f.l10n_latam_identification_type_id, self.nit_type,
            "Empresa debe volver a NIT, no debe conservar la cédula anterior",
        )
