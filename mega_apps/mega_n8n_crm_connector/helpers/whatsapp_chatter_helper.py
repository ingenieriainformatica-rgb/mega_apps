from markupsafe import Markup, escape

def post_whatsapp_note_on_lead(lead, title: str, message: str | None) -> None:
    if not lead or not message:
        return

    safe_title = escape(title)
    safe_message = escape(message).replace("\n", Markup("<br/>"))

    body = Markup(
        """
        <div>
            <p><strong>%s</strong></p>
            <p>%s</p>
        </div>
        """
    ) % (safe_title, safe_message)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
    )

def log_whatsapp_conversation_on_lead(
    lead,
    customer_message: str | None,
    bot_reply: str | None,
    attachment_ids=None,
) -> None:
    if not lead:
        return

    parts = []

    if customer_message:
        parts.append(
            Markup("<p><strong>Cliente por WhatsApp:</strong><br/>%s</p>")
            % escape(customer_message).replace("\n", Markup("<br/>"))
        )

    if bot_reply:
        parts.append(
            Markup("<p><strong>Respuesta automática:</strong><br/>%s</p>")
            % escape(bot_reply).replace("\n", Markup("<br/>"))
        )

    if not parts:
        return

    body = Markup("<div>%s</div>") % Markup("").join(parts)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
        attachment_ids=attachment_ids or None,
    )

def log_customer_message_on_lead_from_session(
    session,
    message: str | None,
    message_id: str | None = None,
) -> bool:
    message = (message or "").strip()
    message_id = (message_id or "").strip()

    if not message:
        return False

    if not session or not session.lead_id:
        return False

    if (
        message_id
        and "last_inbound_message_id" in session._fields
        and session.last_inbound_message_id == message_id
    ):
        return False

    post_whatsapp_message_on_lead(
        session.lead_id,
        "Cliente por WhatsApp",
        message,
    )

    values = {
        "last_message": message,
    }

    if message_id and "last_inbound_message_id" in session._fields:
        values["last_inbound_message_id"] = message_id

    session.write(values)

    return True

def post_whatsapp_message_on_lead(lead, title: str, message: str | None) -> None:
    if not lead or not message:
        return

    safe_title = escape(title)
    safe_message = escape(message).replace("\n", Markup("<br/>"))

    body = Markup(
        """
        <div>
            <p><strong>%s</strong></p>
            <p>%s</p>
        </div>
        """
    ) % (safe_title, safe_message)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
    )
