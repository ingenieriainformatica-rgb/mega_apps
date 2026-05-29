from textwrap import dedent

from .promts.business_context import get_business_context
from .promts.welcome_rules import get_welcome_rules
from .promts.capture_rules import get_capture_rules
from .promts.flow_rules import get_flow_rules
from .promts.catalog_rules import get_catalog_rules
from .promts.json_schema import get_json_schema
from .promts.session_context import get_session_context
from .promts.tone_rules import get_tone_rules


def get_ai_instruction(session, message: str) -> str:
    return dedent(
        f"""
        {get_business_context()}

        ----------------------------------------------------------------

        {get_tone_rules()}

        ----------------------------------------------------------------

        {get_welcome_rules()}

        ----------------------------------------------------------------

        {get_capture_rules()}

        ----------------------------------------------------------------

        {get_flow_rules()}

        ----------------------------------------------------------------

        {get_catalog_rules()}

        ----------------------------------------------------------------

        {get_json_schema()}

        ----------------------------------------------------------------

        {get_session_context(session)}

        ----------------------------------------------------------------

        # MENSAJE DEL CLIENTE

        {message}
        """
    ).strip()
