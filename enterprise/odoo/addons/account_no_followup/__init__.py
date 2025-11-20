import re

from markupsafe import Markup
from . import models


def post_init_hook(env):
    """Replace total_overdue by total_overdue_followup in followup email templates."""
    mail_templates = env['account_followup.followup.line'].search([]).mapped('mail_template_id')
    for template in mail_templates:
        template.body_html = re.sub(
            r'''t-out=("([^"]+)|'([^']+))object\.total_overdue''',
            r't-out=\1object.total_overdue_followup',
            template.body_html,
        )


def uninstall_hook(env):
    """Restore total_overdue instead of total_overdue_followup in followup email templates."""
    mail_templates = env['account_followup.followup.line'].search([]).mapped('mail_template_id')
    for template in mail_templates:
        template.body_html = re.sub(
            r'''t-out=("([^"]+)|'([^']+))object\.total_overdue_followup''',
            r't-out=\1object.total_overdue',
            template.body_html,
        )
