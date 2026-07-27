from odoo import _, models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _init_options_buttons(self, options, previous_options):
        super()._init_options_buttons(options, previous_options)

        # Adds one entry to the report's gear/cog menu (same list the standard "Copy to Documents"
        # button lives in, see documents_account/models/account_report.py for that precedent) instead
        # of touching the standard PDF/XLSX buttons, which stay exactly as core defines them.
        # No 'always_show' key: that's what keeps it out of the toolbar and inside the cog dropdown.
        aged_receivable_report = self.env.ref('account_reports.aged_receivable_report', raise_if_not_found=False)
        if self == aged_receivable_report:
            options['buttons'].append({
                'name': _('XLSX con Cliente, NIT y Fecha por fila'),
                'sequence': 25,
                'action': 'export_file',
                'action_param': 'mega_export_aged_receivable_customer_xlsx',
                'file_export_type': _('XLSX'),
            })

    def mega_export_aged_receivable_customer_xlsx(self, options):
        self.ensure_one()
        # The 'mega_show_partner_name_column' context flag (read in
        # account_aged_partner_balance.py's _custom_options_initializer) is only ever set here, and
        # only for this one call chain: with_context() scopes it to this request alone, so it can
        # never leak into the interactive table, the PDF export, or the standard XLSX button the way
        # a flag stored on `options` could (options get echoed back and reused by the report's
        # on-screen state across later, unrelated requests).
        return self.with_context(mega_show_partner_name_column=True).export_to_xlsx(options)
