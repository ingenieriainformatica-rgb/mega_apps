import logging
from odoo import models, fields, api  # type: ignore

_logger = logging.getLogger(__name__)


class MegaHideGto(models.Model):
    _inherit = 'account.move'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, count=False):
        user = self.env.user
        group_show_special_invoices = self.env.ref('mega_hide_journal_gta.group_show_gto')
        # Verificamos si el usuario pertenece al grupo "Mostrar Facturas Especiales"
        if not group_show_special_invoices in user.groups_id:
            # Si el usuario NO está en el grupo, solo mostrar las facturas de los diarios que no están marcados como "solo para usuarios especiales"
            _logger.info(f"El usuario {user.name} NO está en el grupo, filtrando por diario.")
            domain.append(('journal_id.visible_journal', '=', False))  # Filtra solo los diarios visibles para todos
        # Mostramos los argumentos después de modificar (esto es solo para depuración)
        _logger.info(f"Filtros aplicados: {domain}")
        # Llamamos al search original, pero sin el parámetro 'count'
        return super(MegaHideGto, self)._search(domain, offset=offset, limit=limit, order=order)
