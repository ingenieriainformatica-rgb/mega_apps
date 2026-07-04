import logging
import time

from markupsafe import Markup, escape

from odoo.tools import html2plaintext, plaintext2html  # type: ignore
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation  # type: ignore


_logger = logging.getLogger(__name__)

HUMAN_HANDOFF_STEPS = {"advisor_handoff", "after_hours_handoff"}


def ensure_discuss_channel_for_session(env, session, lead=None, notify_internal=True):
    """Create or reuse the Discuss/WhatsApp channel linked to a WhatsApp session.

    ``notify_internal`` controls whether advisors get added/force-notified
    (chat popup reopened). It stays True for real handoff moments and should
    be False for the automatic per-lead linking that runs on every message.
    """
    if not session:
        return False

    session = session.sudo()
    lead = (lead or session.lead_id).sudo()
    if _is_public_env_user(env):
        _logger.info("[WHATSAPP DISCUSS] Public user detected, using sudo fallback")

    if not lead:
        _logger.info(
            "[WHATSAPP DISCUSS] No lead yet for session=%s phone=%s; channel will not be "
            "linked to any CRM document until a lead exists",
            session.id,
            session.phone,
        )

    _logger.info(
        "[WHATSAPP DISCUSS] Ensuring channel session=%s lead=%s notify_internal=%s",
        session.id,
        lead.id if lead else False,
        notify_internal,
    )

    if session.discuss_channel_id:
        channel = session.discuss_channel_id.sudo()
        if notify_internal:
            _ensure_channel_members(channel, _get_internal_partners(env, lead, channel=channel))
        _post_summary_once(env, session, channel, lead)
        if notify_internal:
            _notify_internal_members(channel)
        _logger.info(
            "[WHATSAPP DISCUSS] Channel reused (cached on session) session=%s channel=%s",
            session.id,
            channel.id,
        )
        return channel

    channel, reused, blocked_reason = _get_or_create_whatsapp_channel(env, session, lead)

    if not channel:
        if blocked_reason == "no_account":
            _logger.warning(
                "[WHATSAPP DISCUSS] No whatsapp.account configured; skipping channel link "
                "(no generic fallback created) session=%s phone=%s",
                session.id,
                session.phone,
            )
            return False
        channel = _create_internal_discuss_channel(env, session, lead)
        reused = False

    if not channel:
        return False

    if reused and lead:
        _post_channel_reused_note_on_lead(env, lead, channel)

    session.write({"discuss_channel_id": channel.id})
    if notify_internal:
        _ensure_channel_members(channel, _get_internal_partners(env, lead, channel=channel))
    _post_summary_once(env, session, channel, lead)
    if notify_internal:
        _notify_internal_members(channel)
    _logger.info(
        "[WHATSAPP DISCUSS] Channel %s session=%s channel=%s",
        "reused (native)" if reused else "created",
        session.id,
        channel.id,
    )
    return channel


def ensure_discuss_channel_for_handoff(env, session, lead=None):
    """Backward-compatible wrapper used by the existing handoff flow."""
    if not session or session.step not in HUMAN_HANDOFF_STEPS:
        return False
    return ensure_discuss_channel_for_session(env, session, lead=lead)


def post_inbound_whatsapp_message_to_discuss(env, session, message_text, wa_message_id=None):
    """Post an inbound customer WhatsApp message on the session Discuss channel."""
    if not session:
        return False

    session = session.sudo()
    message_text = (message_text or "").strip()
    wa_message_id = (wa_message_id or "").strip()

    if not message_text:
        _logger.info(
            "[WHATSAPP DISCUSS] No message text, skipping post session=%s",
            session.id,
        )
        return False

    channel = ensure_discuss_channel_for_session(env, session, lead=session.lead_id)
    if not channel:
        return False

    if (
        wa_message_id
        and "last_inbound_message_id" in session._fields
        and session.last_inbound_message_id == wa_message_id
    ):
        _logger.info(
            "[WHATSAPP DISCUSS] Duplicate inbound ignored session=%s message_id=%s",
            session.id,
            wa_message_id,
        )
        _notify_internal_members(channel)
        return False

    if wa_message_id and _whatsapp_message_exists(env, wa_message_id):
        _logger.info(
            "[WHATSAPP DISCUSS] Duplicate inbound ignored session=%s message_id=%s",
            session.id,
            wa_message_id,
        )
        _notify_internal_members(channel)
        return False

    message_log = False
    if wa_message_id:
        message_log, reserved = env["mega.whatsapp.message.log"].sudo().reserve_once(
            wa_message_id,
            "inbound",
            phone=session.phone,
            message_body=message_text,
            session_id=session.id,
            channel_id=channel.id,
        )
        if not reserved:
            _logger.info(
                "[WHATSAPP DISCUSS] Duplicate inbound ignored session=%s message_id=%s log=%s",
                session.id,
                wa_message_id,
                message_log.id,
            )
            _notify_internal_members(channel)
            return False

    author_id = (
        channel.whatsapp_partner_id.id
        if channel.channel_type == "whatsapp" and channel.whatsapp_partner_id
        else _get_author_partner_id(env)
    )
    message_kwargs = {
        "body": plaintext2html(message_text),
        "subtype_xmlid": "mail.mt_comment",
        "author_id": author_id or None,
    }

    if channel.channel_type == "whatsapp" and wa_message_id:
        message_kwargs["message_type"] = "whatsapp_message"
        message_kwargs["whatsapp_inbound_msg_uid"] = wa_message_id
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Native pattern found in %s",
            "enterprise/odoo/addons/whatsapp/models/whatsapp_account.py::_process_messages",
        )
    else:
        # Without Meta's message id, never use whatsapp_message: Odoo would treat it
        # as outbound and could send it back to the customer.
        message_kwargs["message_type"] = "comment"

    try:
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Posting inbound channel=%s session=%s",
            channel.id,
            session.id,
        )
        with env.cr.savepoint():
            mail_message = channel.sudo().message_post(**message_kwargs)
        if message_log:
            message_log.sudo().write({"mail_message_id": mail_message.id})
        _notify_internal_members(channel)
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Message created id=%s model=%s res_id=%s type=%s subtype=%s",
            mail_message.id,
            mail_message.model,
            mail_message.res_id,
            mail_message.message_type,
            mail_message.subtype_id.display_name if mail_message.subtype_id else False,
        )
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Channel members=%s",
            channel.sudo().channel_member_ids.sudo().mapped("partner_id").ids,
        )
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Bus notification sent channel=%s message=%s",
            channel.id,
            mail_message.id,
        )
        _logger.info(
            "[WHATSAPP DISCUSS REALTIME] Realtime fallback skipped reason=%s",
            "native_discuss_channel_message_post",
        )
        _logger.info(
            "[WHATSAPP DISCUSS] Inbound posted session=%s channel=%s mail_message=%s message_id=%s",
            session.id,
            channel.id,
            mail_message.id,
            wa_message_id or False,
        )
        return True
    except Exception:
        _logger.exception(
            "[WHATSAPP DISCUSS] Failed to post inbound session=%s channel=%s message_id=%s",
            session.id,
            channel.id,
            wa_message_id or False,
        )
        return False


def post_inbound_whatsapp_media_to_discuss(
    env,
    session,
    message_text,
    *,
    filename,
    media_content,
    wa_message_id=None,
    voice=False,
):
    """Post inbound WhatsApp media using Odoo's native WhatsApp message path."""
    if not session:
        return False

    session = session.sudo()
    message_text = (message_text or "").strip()
    wa_message_id = (wa_message_id or "").strip()
    filename = (filename or "whatsapp_media").strip()
    media_content = media_content or b""

    if not media_content:
        _logger.warning(
            "[WHATSAPP DISCUSS] No media content, skipping media post session=%s message_id=%s",
            session.id,
            wa_message_id or False,
        )
        return False

    channel = ensure_discuss_channel_for_session(env, session, lead=session.lead_id)
    if not channel:
        return False

    if wa_message_id and _whatsapp_message_exists(env, wa_message_id):
        _logger.info(
            "[WHATSAPP DISCUSS] Duplicate media inbound ignored session=%s message_id=%s",
            session.id,
            wa_message_id,
        )
        _notify_internal_members(channel)
        return False

    author_id = (
        channel.whatsapp_partner_id.id
        if channel.channel_type == "whatsapp" and channel.whatsapp_partner_id
        else _get_author_partner_id(env)
    )
    message_kwargs = {
        "body": plaintext2html(message_text) if message_text else "",
        "subtype_xmlid": "mail.mt_comment",
        "author_id": author_id or None,
        "attachments": [(filename, media_content, {"voice": bool(voice)})],
    }

    if channel.channel_type == "whatsapp" and wa_message_id:
        message_kwargs["message_type"] = "whatsapp_message"
        message_kwargs["whatsapp_inbound_msg_uid"] = wa_message_id
    else:
        message_kwargs["message_type"] = "comment"

    try:
        _logger.info(
            "[WHATSAPP DISCUSS] Posting inbound media channel=%s type=%s filename=%s message_id=%s",
            channel.id,
            channel.channel_type,
            filename,
            wa_message_id or False,
        )
        with env.cr.savepoint():
            mail_message = channel.sudo().message_post(**message_kwargs)
        _notify_internal_members(channel)
        _logger.info(
            "[WHATSAPP MEDIA] message posted id=%s attachment_ids=%s",
            mail_message.id if mail_message else False,
            mail_message.attachment_ids.ids if mail_message else [],
        )
        for attachment in mail_message.attachment_ids:
            _logger.info(
                "[WHATSAPP MEDIA] attachment created id=%s name=%s res_model=%s res_id=%s",
                attachment.id,
                attachment.name,
                attachment.res_model,
                attachment.res_id,
            )
        return mail_message
    except Exception:
        _logger.exception(
            "[WHATSAPP DISCUSS] Failed to post inbound media session=%s channel=%s message_id=%s",
            session.id,
            channel.id,
            wa_message_id or False,
        )
        return False


def post_outbound_whatsapp_message_to_discuss(env, session, message_text, attachment_ids=None):
    """Post an outbound bot/advisor message on Discuss without sending it to Meta."""
    if not session:
        return False

    session = session.sudo()
    message_text = (message_text or "").strip()
    attachment_ids = attachment_ids or []
    if not message_text and not attachment_ids:
        _logger.info(
            "[WHATSAPP DISCUSS] No message text, skipping post session=%s",
            session.id,
        )
        return False

    channel = ensure_discuss_channel_for_session(env, session, lead=session.lead_id)
    if not channel:
        return False

    channel.sudo().message_post(
        body=plaintext2html(message_text),
        message_type="comment",
        subtype_xmlid="mail.mt_comment",
        author_id=_get_author_partner_id(env) or None,
        attachment_ids=attachment_ids or None,
    )
    _notify_internal_members(channel)
    _logger.info("[WHATSAPP DISCUSS] Outbound posted session=%s", session.id)
    return True


def log_inbound_message_on_discuss_channel(session, message, message_id=None):
    """Backward-compatible wrapper for previous callers."""
    if not session:
        return False
    return post_inbound_whatsapp_message_to_discuss(
        session.env,
        session,
        message,
        wa_message_id=message_id,
    )


def _get_or_create_whatsapp_channel(env, session, lead):
    """Return (channel_or_False, reused, blocked_reason).

    ``blocked_reason`` is "no_account"/"no_phone" when no channel could be
    resolved at all, or None otherwise. The existence check is done
    ourselves (by whatsapp_number + wa_account_id, without a
    related_message) before calling the native method: the native
    ``_get_whatsapp_channel`` filters an existing channel by "responsible
    partners" when related_message is passed, and can create a duplicate
    channel for the same number if the responsible partners don't match.
    """
    account = _get_whatsapp_account(env, session)
    if not account:
        _logger.warning(
            "[WHATSAPP DISCUSS] No whatsapp.account found in system; cannot resolve "
            "WhatsApp channel session=%s phone=%s phone_number_id=%s",
            session.id,
            session.phone,
            session.phone_number_id,
        )
        return False, False, "no_account"

    phone = _normalize_whatsapp_phone(session.phone)
    if not phone:
        _logger.warning(
            "[WHATSAPP DISCUSS] Empty/invalid phone, cannot resolve WhatsApp channel session=%s",
            session.id,
        )
        return False, False, "no_phone"

    wa_formatted = _format_whatsapp_number_like_native(env, phone)

    existing_channel = env["discuss.channel"].sudo().search(
        [
            ("whatsapp_number", "=", wa_formatted),
            ("wa_account_id", "=", account.id),
        ],
        order="create_date desc",
        limit=1,
    )
    if existing_channel:
        _logger.info(
            "[WHATSAPP DISCUSS] Found existing WhatsApp channel=%s for phone=%s account=%s session=%s",
            existing_channel.id,
            wa_formatted,
            account.id,
            session.id,
        )
        return existing_channel, True, None

    is_handoff = session.step in HUMAN_HANDOFF_STEPS
    related_message = (
        _get_related_message_for_whatsapp_channel(env, lead, is_handoff=is_handoff)
        if lead
        else env["mail.message"].sudo().browse()
    )
    channel = env["discuss.channel"].sudo()._get_whatsapp_channel(
        whatsapp_number=phone,
        wa_account_id=account.sudo(),
        sender_name=(session.customer_name or "").strip() or False,
        create_if_not_found=True,
        related_message=related_message,
    )
    _logger.info(
        "[WHATSAPP DISCUSS] Created new WhatsApp channel=%s for phone=%s account=%s session=%s",
        channel.id if channel else False,
        wa_formatted,
        account.id,
        session.id,
    )
    return channel, False, None


def _format_whatsapp_number_like_native(env, phone):
    base_number = phone if phone.startswith("+") else f"+{phone}"
    formatted = wa_phone_validation.wa_phone_format(
        env.company,
        number=base_number,
        force_format="WHATSAPP",
        raise_exception=False,
    )
    return formatted or phone


def _create_internal_discuss_channel(env, session, lead):
    partner_ids = _get_internal_partners(env, lead).ids
    if not partner_ids:
        _logger.warning(
            "[WHATSAPP DISCUSS] No internal users found, creating channel without members session=%s",
            session.id,
        )

    return env["discuss.channel"].sudo().create(
        {
            "name": _build_channel_name(session, lead),
            "channel_type": "group",
            "channel_member_ids": [
                (0, 0, {"partner_id": partner_id}) for partner_id in partner_ids
            ],
        }
    )


def _get_related_message_for_whatsapp_channel(env, lead, is_handoff=False):
    if lead:
        text = (
            "Conversacion WhatsApp entregada a asesor humano."
            if is_handoff
            else "Canal de WhatsApp vinculado automáticamente a este lead."
        )
        return lead.sudo().message_post(
            body=Markup("<p>%s</p>") % text,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
    return env["mail.message"].sudo().browse()


def _post_channel_reused_note_on_lead(env, lead, channel):
    if not lead or not channel:
        return False

    # Same markup/class Odoo's native whatsapp module uses for its own
    # "new channel" chatter link, so clicking it opens the conversation
    # in place (and auto-joins the user) instead of just navigating away.
    channel_url = f"{_get_base_url(env)}/odoo/discuss.channel/{channel.id}"
    lead.sudo().message_post(
        body=Markup(
            '<p>Este lead se vinculó a un canal de WhatsApp existente, '
            'creado previamente para el mismo número de teléfono: '
            '<a target="_blank" class="o_whatsapp_channel_redirect" '
            'data-oe-id="%s" href="%s">%s</a></p>'
        ) % (channel.id, escape(channel_url), escape(channel.display_name)),
        message_type="comment",
        subtype_xmlid="mail.mt_note",
    )
    _logger.info(
        "[WHATSAPP DISCUSS] Reused-channel note posted on lead=%s channel=%s",
        lead.id,
        channel.id,
    )
    return True


def _post_summary_once(env, session, channel, lead):
    if not channel or not session or "discuss_summary_posted" not in session._fields:
        return False

    if session.discuss_summary_posted:
        return False

    lead_link = Markup("Sin lead vinculado")
    if lead:
        lead_url = _get_lead_url(env, lead)
        lead_link = Markup('<a target="_blank" href="%s">%s</a>') % (
            escape(lead_url),
            escape(lead.display_name),
        )

    body = Markup(
        """
        <div>
            <p><strong>💬 Nuevo lead de WhatsApp</strong></p>
            <p>
                <strong>Cliente:</strong> %s<br/>
                <strong>Teléfono:</strong> %s<br/>
                <strong>Ubicación:</strong> %s<br/>
                <strong>Vehículo:</strong> %s<br/>
                <strong>Lead CRM:</strong> %s<br/>
                <strong>Estado:</strong> %s
            </p>
            <p><strong>Resumen:</strong><br/>%s</p>
        </div>
        """
    ) % (
        escape(session.customer_name or "Sin nombre"),
        escape(session.phone or ""),
        escape(session.location or session.neighborhood or session.city or "Sin ubicación"),
        escape(_get_vehicle_label(session)),
        lead_link,
        escape(session.step or ""),
        escape(
            session.conversation_summary
            or session.relevant_data
            or _get_recent_lead_history(lead)
            or session.last_message
            or "Sin resumen disponible."
        ).replace("\n", Markup("<br/>")),
    )

    channel.sudo().message_post(
        body=body,
        message_type="comment",
        subtype_xmlid="mail.mt_comment",
        author_id=_get_author_partner_id(env) or None,
    )
    session.write({"discuss_summary_posted": True})
    _logger.info(
        "[WHATSAPP DISCUSS] Summary posted session=%s channel=%s",
        session.id,
        channel.id,
    )
    return True


def _whatsapp_message_exists(env, wa_message_id):
    return bool(
        wa_message_id
        and env["whatsapp.message"].sudo().search_count([("msg_uid", "=", wa_message_id)])
    )


def _get_whatsapp_account(env, session):
    Account = env["whatsapp.account"].sudo()
    phone_number_id = (session.phone_number_id or "").strip()
    account = Account.search([("phone_uid", "=", phone_number_id)], limit=1) if phone_number_id else Account
    return account or Account.search([], limit=1)


def _normalize_whatsapp_phone(phone):
    return "".join(char for char in (phone or "") if char.isdigit())


def _get_internal_partners(env, lead, channel=False):
    Partner = env["res.partner"].sudo()
    partners = Partner

    if lead:
        lead_user = lead.sudo().user_id.sudo()
        if _is_internal_user(lead_user):
            partners |= lead_user.partner_id.sudo()

    if channel and channel.channel_type == "whatsapp" and channel.wa_account_id:
        notify_users = _filter_internal_users(channel.sudo().wa_account_id.sudo().notify_user_ids.sudo())
        partners |= notify_users.partner_id.sudo()

    if not partners:
        configured_users = _get_configured_internal_users(env)
        partners |= configured_users.partner_id.sudo()

    if not partners:
        admin_partner = _get_admin_partner(env)
        if admin_partner:
            partners |= admin_partner

    partners = partners.sudo().filtered(_partner_has_internal_user)
    _logger.info(
        "[WHATSAPP DISCUSS] Internal users selected: %s",
        ", ".join(partners.mapped("name")) if partners else "none",
    )
    return partners


def _ensure_channel_members(channel, partners):
    if not channel or not partners:
        return

    channel = channel.sudo()
    partners = partners.sudo().filtered(_partner_has_internal_user)
    if not partners:
        _logger.warning(
            "[WHATSAPP DISCUSS] No valid internal partners to add channel=%s",
            channel.id,
        )
        return

    missing_partners = partners - channel.channel_member_ids.sudo().partner_id.sudo()
    if missing_partners:
        channel.sudo().add_members(
            partner_ids=missing_partners.ids,
            open_chat_window=True,
            post_joined_message=False,
        )

    target_partner_ids = set(partners.ids)
    target_members = channel.channel_member_ids.sudo().filtered(
        lambda member: member.sudo().partner_id.sudo().id in target_partner_ids
    )
    _open_internal_channel_members(target_members)


def _notify_internal_members(channel):
    channel = channel.sudo()
    internal_members = channel.channel_member_ids.sudo().filtered(
        lambda member: _partner_has_internal_user(member.sudo().partner_id.sudo())
    )
    _open_internal_channel_members(internal_members)

    internal_partner_ids = internal_members.sudo().partner_id.sudo().ids
    if internal_partner_ids:
        channel.sudo()._broadcast(internal_partner_ids)


def _open_internal_channel_members(members):
    members = members.sudo().filtered(
        lambda member: _partner_has_internal_user(member.sudo().partner_id.sudo())
    )
    if not members:
        return

    _logger.info(
        "[WHATSAPP DISCUSS] Opening internal members channel=%s partners=%s",
        members[:1].channel_id.id,
        ", ".join(members.sudo().partner_id.sudo().mapped("name")),
    )
    for member in members:
        _force_open_chat_window(member)


def _force_open_chat_window(member):
    member = member.sudo()
    if member.unpin_dt:
        member.sudo().write({"unpin_dt": False})
    member.sudo()._channel_fold("open", int(time.time()))


def _get_author_partner_id(env):
    user = env.user.sudo()
    if _is_internal_user(user):
        return user.partner_id.sudo().id

    if _is_public_env_user(env):
        _logger.info("[WHATSAPP DISCUSS] Public user detected, using sudo fallback")

    admin_partner = _get_admin_partner(env)
    return admin_partner.id if admin_partner else False


def _is_public_env_user(env):
    user = env.user.sudo()
    return bool(user and user._is_public())


def _is_internal_user(user):
    user = user.sudo()
    return bool(
        user
        and user.exists()
        and user.active
        and not user.share
        and not user._is_public()
        and user.partner_id
        and user.partner_id.active
    )


def _filter_internal_users(users):
    return users.sudo().filtered(_is_internal_user)


def _partner_has_internal_user(partner):
    partner = partner.sudo()
    return bool(
        partner
        and partner.exists()
        and partner.active
        and _filter_internal_users(partner.user_ids.sudo())
    )


def _get_configured_internal_users(env):
    config = env["ir.config_parameter"].sudo()
    group_xmlid = (
        config.get_param("mega_n8n_crm_connector.whatsapp_discuss_internal_group_xmlid")
        or config.get_param("mega_whatsapp_discuss_internal_group_xmlid")
        or ""
    ).strip()
    if not group_xmlid:
        return env["res.users"].sudo().browse()

    group = env.ref(group_xmlid, raise_if_not_found=False)
    if not group:
        _logger.warning("[WHATSAPP DISCUSS] Configured group not found: %s", group_xmlid)
        return env["res.users"].sudo().browse()

    return _filter_internal_users(group.sudo().users.sudo())


def _get_admin_partner(env):
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    admin = admin.sudo() if admin else admin
    if _is_internal_user(admin):
        return admin.partner_id.sudo()
    return env["res.partner"].sudo().browse()


def _build_channel_name(session, lead):
    label = (session.customer_name or session.phone or f"Sesión {session.id}").strip()
    return f"WhatsApp - {label} - {lead.name}" if lead else f"WhatsApp - {label}"


def _get_vehicle_label(session):
    parts = [
        session.vehicle_brand or "",
        session.vehicle_model or "",
        session.vehicle_year or "",
    ]
    vehicle = " ".join(part for part in parts if part).strip()
    return vehicle or session.vehicle_info or "Sin vehículo"


def _get_recent_lead_history(lead, limit=8):
    if not lead:
        return ""

    messages = lead.env["mail.message"].sudo().search(
        [
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            "|",
            "|",
            ("body", "ilike", "WhatsApp"),
            ("body", "ilike", "Cliente por WhatsApp"),
            ("body", "ilike", "Respuesta automática"),
        ],
        order="id desc",
        limit=limit,
    )
    lines = []
    for message in reversed(messages):
        text = html2plaintext(message.body or "").strip()
        if text:
            lines.append(text)
    return "\n\n".join(lines)


def _get_base_url(env):
    return (
        env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
    ).rstrip("/")


def _get_lead_url(env, lead):
    if not lead:
        return ""

    path = f"/odoo/crm.lead/{lead.id}"
    return f"{_get_base_url(env)}{path}" if _get_base_url(env) else path
