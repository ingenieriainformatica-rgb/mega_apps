import logging
from odoo import models  #type: ignore

_logger = logging.getLogger(__name__)


class GeneralLedgerNIT(models.AbstractModel):
    _inherit = 'account.report'

    def _get_lines(self, options, line_id=None, *args, **kwargs):
        # lines = super()._get_lines(options, line_id=line_id, *args, **kwargs)

        _logger.info("\n\n GeneralLedgerNIT _get_lines called with lines \n\n")

        # for line in lines:
        #     # Solo líneas con modelo
        #     if line.get('model') != 'account.move.line':
        #         continue

        #     record_id = line.get('id')
        #     if not record_id:
        #         continue

        #     aml = self.env['account.move.line'].browse(record_id)

        #     if not aml.exists():
        #         continue

        #     vat = aml.partner_id.vat or ''

        #     if 'columns' in line:
        #         line['columns'].append({
        #             'name': vat,
        #             'no_format': vat,
        #         })

        return ""