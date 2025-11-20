import logging
import calendar
from datetime import date as pydate, datetime as pydt
from odoo.addons.industry_real_estate import const
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MonthlyInvoicer(models.Model):
    _name = "monthly.invoicer"
    _description = "Generador mensual de órdenes y emisiones ECOERP"
    _check_company_auto = True

    # Estados en los que se permite realizar cobro / proceso automático
    STATES_TO_PAY = const.SATES_TO_PAY

    # =========================
    # ENTRADA DEL CRON
    # =========================
    def cron_monthly_invoicing(self):
        """Punto de entrada del cron: recorre compañías y ejecuta el pipeline."""
        target_date = fields.Date.context_today(self)
        companies = self.env['res.company'].sudo().search([])

        for company in companies:
            try:
                self.with_context(
                    allowed_company_ids=[company.id],
                    company_id=company.id,
                    from_cron=True,
                    target_date=target_date,
                ).sudo()._run_pipeline()
            except Exception as e:
                _logger.exception("Cron ECOERP falló para compañía %s: %s", company.display_name, e)
                # continuar con las demás compañías

    # =========================
    # PIPELINE PRINCIPAL
    # =========================
    def _run_pipeline(self):
        """1) obtener contratos vigentes, 2) generar órdenes, 3) emitir documentos."""
        target_date = self.env.context.get('target_date') or fields.Date.context_today(self)
        contracts = self._get_live_contracts()

        _logger.info("[ECOERP] %s contratos vigentes detectados en %s", len(contracts), self.env.company.display_name)

        for contract in contracts:
            try:
                # 2) Generación de órdenes (simple/directa para pruebas)
                gen_result = self._generate_orders_for_contract(contract, target_date)

                # 3) Emisión de documentos en borrador (según tipo de orden)
                self._emit_documents_for_orders(gen_result, target_date)

            except Exception as e:
                _logger.exception("[ECOERP] Error procesando contrato %s: %s", contract.display_name, e)
                continue

    # =========================
    # 1) CONTRATOS VIGENTES
    # =========================
    def _get_live_contracts(self):
        """Contratos (sale.order) vigentes: ecoerp_contract=True y estado en STATES_TO_PAY."""
        domain = [
            ('ecoerp_contract', '=', True),
            ('state', 'in', self.STATES_TO_PAY),
            ('company_id', '=', self.env.company.id),
        ]
        # Ajusta el modelo si tu “contrato” no es sale.order
        return self.env['sale.order'].sudo().search(domain)

    # =========================
    # 2) GENERAR ÓRDENES
    # =========================
    def _generate_orders_for_contract(self, contract, target_date):
        """
        Genera órdenes para el contrato.
        Fase de pruebas: generación directa y mínima; luego conectarás reglas/fechas/params.
        Devuelve un dict con recordsets generados para seguimiento en la emisión.
        """
        # ⚙️ Hooks de configuración (los conectarás luego por ir.config_parameter / res.company):
        # - porcentajes, IPC, mora, comisiones, etc.
        # - ventanas de fechas
        # En esta fase los omitimos; dejamos el gancho.

        generated = {
            'sale_orders': self.env['sale.order'],          # recordset vacío
            'purchase_orders': self.env['purchase.order'],  # recordset vacío
        }

        # 2.1) Intenta usar un generador específico del contrato si existe
        custom_gen = getattr(contract, '_ecoerp_generate_monthly_orders', None)
        if callable(custom_gen):
            res = custom_gen(target_date=target_date, from_cron=True)
            # Se espera que devuelva dict similar a generated
            if isinstance(res, dict):
                generated['sale_orders'] |= res.get('sale_orders', self.env['sale.order'])
                generated['purchase_orders'] |= res.get('purchase_orders', self.env['purchase.order'])
                return generated

        # 2.2) Si no hay generador específico, intenta tu acción existente (si la tienes)
        # gen_action = getattr(contract, 'action_generate_orders', None)
        # if callable(gen_action):
        #     try:
        #         # Mantengo simple: generación “directa” para pruebas
        #         # (confirmación/facturación la manejamos en la fase 3)
        #         res2 = gen_action(date=target_date, confirm_orders=False, create_invoices=False)
        #         if isinstance(res2, dict):
        #             generated['sale_orders'] |= res2.get('sale_orders', self.env['sale.order'])
        #             generated['purchase_orders'] |= res2.get('purchase_orders', self.env['purchase.order'])
        #     except Exception:
        #         _logger.exception("[ECOERP] action_generate_orders falló en %s", contract.display_name)

        # 2.3) Si tu generador no devuelve las órdenes, intenta inferirlas por vínculo
        if not generated['sale_orders'] and hasattr(contract, 'id'):
            so_linked = self.env['sale.order'].sudo().search([
                ('contract_id', '=', contract.id),
                ('ecoerp_contract', '=', False),
                ('company_id', '=', self.env.company.id),
                ('state', 'not in', ['cancel']),
            ])
            generated['sale_orders'] |= so_linked

        if not generated['purchase_orders'] and hasattr(contract, 'id'):
            po_linked = self.env['purchase.order'].sudo().search([
                ('contract_id', '=', contract.id),
                ('company_id', '=', self.env.company.id),
                ('state', 'not in', ['cancel']),
            ])
            generated['purchase_orders'] |= po_linked

        return generated

    # =========================
    # 3) EMISIÓN DE DOCUMENTOS
    # =========================
    def _emit_documents_for_orders(self, generated, target_date):
        """
        Emite documentos (venta/compra) a partir de las órdenes generadas.
        **De momento**:
          - Confirmamos órdenes si están en borrador.
          - Creamos facturas/bills en borrador (no se publican).
          - NO aplicamos aún “tiempo de espera” (lo conectarás luego por configuración).
        """
        sale_orders = (generated or {}).get('sale_orders', self.env['sale.order'])
        purchase_orders = (generated or {}).get('purchase_orders', self.env['purchase.order'])

        # 3.1) Órdenes de VENTA → facturas cliente en borrador - enviadas
        sale_orders_to_confirm = sale_orders.filtered(lambda s: s.state in ('draft', 'sent'))
        for so in sale_orders_to_confirm:
            try:
                # Confirmar OV para habilitar facturación
                _logger.info("[ECOERP] Confirmando SO %s", so.name)
                so.sudo().action_confirm()

                # Crear factura (dejar en borrador)
                # Compatibilidad: intenta primero acción pública; si no, usa método técnico
                create_inv = getattr(so, 'action_create_invoice', None)
                _logger.info("[ECOERP] Creando factura para SO %s", so.name)
                if callable(create_inv):
                    create_inv()
                else:
                    create_inv2 = getattr(so, '_create_invoices', None)
                    if callable(create_inv2):
                        moves = create_inv2(final=False)  # deja en borrador
                        # Opcional: setear fecha/diario por contexto
                        _logger.info("[ECOERP] Facturas de venta creadas (borrador) para SO %s: %s",
                                     so.name, ','.join(moves.mapped('name')) if moves else '—')
            except Exception:
                _logger.exception("[ECOERP] Emisión ventas falló para SO %s", so.display_name)

        # 3.2) Órdenes de COMPRA → factura proveedor en borrador - enviadas
        purchase_orders_to_confirm = purchase_orders.filtered(lambda p: p.state in ('draft', 'sent'))
        for po in purchase_orders_to_confirm:
            try:
                # Confirmar OC para habilitar facturación proveedor
                confirm_po = getattr(po, 'button_confirm', None)
                if callable(confirm_po):
                    _logger.info("[ECOERP] Confirmando PO %s", po.name)
                    po.sudo().button_confirm()

                # Crear bill (borrador)
                create_bill = getattr(po, 'action_create_invoice', None)
                _logger.info("[ECOERP] Creando bill para PO %s", po.name)
                if callable(create_bill):
                    create_bill()
                else:
                    create_bill2 = getattr(po, '_create_invoices', None)
                    if callable(create_bill2):
                        moves = create_bill2()
                        _logger.info("[ECOERP] Bills de compra creados (borrador) para PO %s: %s",
                                     po.name, ','.join(moves.mapped('name')) if moves else '—')
            except Exception:
                _logger.exception("[ECOERP] Emisión compras falló para PO %s", po.display_name)
