import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import (
    anon_feedback_menu,
    back_to_start,
    contact_menu,
    info_menu,
    main_menu,
    policies_menu,
)
from bot.utils.helpers import safe_edit

logger = logging.getLogger(__name__)

# ── Reusable text blocks ──────────────────────────────────────────────────────

_WELCOME = "🚀 *RSAF WINGS DIGITAL ASSISTANT*\nHow can we support you today?"

_INFO = (
    "📱 *RSAF WINGS INFORMATION*\n\n"
    "RSAF WINGS (Women INspiring Growth and Support) is the RSAF servicewomen "
    "network rebranded in 2021.\n"
    "It brings together support, development, and engagement for servicewomen "
    "across their careers.\n\n"
    "🚀 *What WINGS covers*\n"
    "• Career development and progression\n"
    "• Wellbeing and workplace support\n"
    "• Inclusion and community building\n"
    "• Feedback and clarification channels"
)

_MENTORSHIP = (
    "🌱 *MENTORSHIP PROGRAMMES*\n\n"
    "• *Ascend Programme*\n"
    "Early career support through BMT and ab-initio training.\n\n"
    "• *Vanguard Programme*\n"
    "1-to-1 mentorship post ab-initio training focusing on career growth and networks."
)

_POLICIES = "📋 *POLICIES & GUIDELINES*\n\nSelect a topic:"

_DRESS = (
    "📋 *DRESS CODE*\n\n"
    "• Smart casual or formal attire\n"
    "• Follow your unit's dress regulations\n"
    "• Neat and professional grooming at all times"
)

_NURSING = (
    "🤱 *NURSING ROOM*\n\n"
    "• Designated nursing rooms available at HQ\n"
    "• Accessible during office hours\n"
    "• Contact your unit admin for location details"
)

_HARASSMENT = (
    "⚠️ *HARASSMENT & MISCONDUCT*\n\n"
    "All cases are handled with strict confidentiality.\n\n"
    "Report through:\n"
    "• Official MINDEF/SAF channels\n"
    "• Your WINGS representative\n"
    "• Anonymous feedback form (see Contact & Channels)"
)

_CONTACT = "📲 *CONTACT & CHANNELS*\n\nStay connected with RSAF WINGS:"

_CHANNEL = "📢 *TELEGRAM CHANNEL*\n\nhttps://t.me/+7YV2dqpmrvRlMjQ1"

_EMAIL = "📧 *OSN EMAIL*\n\nRSAFWINGS@defence.gov.sg"

_ANON_FEEDBACK = (
    "📝 *ANONYMOUS FEEDBACK*\n\n"
    "Submit securely and confidentially.\n"
    "No login required."
)

# ── Route map: callback_data → (text, keyboard_fn, parse_mode) ───────────────

_ROUTES: dict[str, tuple[str, callable, str | None]] = {
    "menu":         (_WELCOME,        main_menu,        "Markdown"),
    "info":         (_INFO,           info_menu,        "Markdown"),
    "mentorship":   (_MENTORSHIP,     back_to_start,    "Markdown"),
    "policies":     (_POLICIES,       policies_menu,    "Markdown"),
    "dress":        (_DRESS,          back_to_start,    "Markdown"),
    "nursing":      (_NURSING,        back_to_start,    "Markdown"),
    "harassment":   (_HARASSMENT,     back_to_start,    "Markdown"),
    "contact":      (_CONTACT,        contact_menu,     "Markdown"),
    "channel":      (_CHANNEL,        back_to_start,    None),
    "email":        (_EMAIL,          back_to_start,    None),
    "anon_feedback":(_ANON_FEEDBACK,  anon_feedback_menu, "Markdown"),
}


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    try:
        await query.answer()
    except Exception as exc:
        logger.warning("Stale callback ignored: %s", exc)
        return

    route = _ROUTES.get(query.data)
    if route is None:
        logger.warning("Unknown callback_data: %s", query.data)
        return

    text, keyboard_fn, parse_mode = route
    await safe_edit(query, text, keyboard_fn(), parse_mode)
