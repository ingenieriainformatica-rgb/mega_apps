from odoo import models

class SaleOrderCustomReport(models.AbstractModel):
    _name = "report.sale_order_custom_report.sale_order_template"
    _description = "Custom Sale Order QWeb Report"

    def _get_report_values(self, docids, data=None):
        print("im here")
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
        }
