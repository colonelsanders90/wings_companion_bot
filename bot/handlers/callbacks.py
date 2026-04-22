import logging

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import (
    anon_feedback_menu,
    back_to_contact,
    back_to_health,
    back_to_info,
    back_to_policies,
    back_to_start,
    contact_menu,
    health_menu,
    info_menu,
    main_menu,
    nursing_back_menu,
    policies_menu,
    welfare_menu,
)
from bot.utils.helpers import safe_edit
from bot.utils.rate_limiter import rate_limit

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

_HEALTH = "💪 *HEALTH & FITNESS*\n\nSelect a topic:"

_IPPT = (
    "🏃 *IPPT STANDARDS (FEMALE)*\n\n"
    "IPPT consists of 3 stations:\n"
    "• *Push-ups* — bent-knee (1 min)\n"
    "• *Sit-ups* (1 min)\n"
    "• *2.4 km Run*\n\n"
    "🏅 *Award Levels*\n"
    "• 🥇 Gold — ≥ 85 points _(+$300 incentive)_\n"
    "• 🥈 Silver — 75–84 points _(+$200 incentive)_\n"
    "• ✅ Pass — 51–74 points\n"
    "• ❌ Fail — < 51 points\n\n"
    "Point requirements ease across 14 age groups (below 22 through 58–60).\n\n"
    "🔖 *Exemptions for Servicewomen*\n"
    "_(AFTD 01/15)_\n\n"
    "Uniformed regular servicewomen are exempted under any of the following:\n\n"
    "*(a)* In a state of *pregnancy*, with IRB approval for temporary exemption.\n\n"
    "*(b)* *Combat vocationalists* within the one-year post-delivery or miscarriage period.\n\n"
    "*(c)* *Non-combat vocationalists* who are:\n"
    "  — On post-delivery or miscarriage (any age), with IRB approval for permanent exemption; or\n"
    "  — Aged *35 and above* as at 1 Apr of the Physical Fitness Test Window.\n\n"
    "_Verify exact score cutoffs for your age group on the official NS Portal IPPT calculator._"
)

_BMI = (
    "⚖️ *BMI STANDARDS*\n\n"
    "BMI = weight (kg) ÷ height² (m²)\n\n"
    "📊 *BMI Categories*\n"
    "• < 18.5 — Underweight\n"
    "• 18.5 – 24.9 — Normal Weight\n"
    "• 25.0 – 26.9 — Overweight (Mild)\n"
    "• 27.0 – 29.9 — Overweight (Moderate)\n"
    "• 30.0 – 32.4 — Obese\n"
    "• 32.5 – 39.9 — Severely Obese\n"
    "• ≥ 40.0 — Very Severely Obese\n\n"
    "🔖 *Exemptions for Servicewomen*\n"
    "_(JMD No. 4-6(A))_\n\n"
    "Servicewomen who are *pregnant* (certified by a gynaecologist or obstetrician "
    "with the estimated date of delivery) are *automatically exempted* from BMI "
    "measurement — no exemption request needed.\n\n"
    "They will resume BMI monitoring in the following workyear post-delivery.\n\n"
    "_BMI is a general screening tool. For personalised health advice, consult your MO._"
)

_WELFARE = "🤱 *FACILITIES & SUPPORT*\n\nSelect a topic:"

_NURSING_PROMPT = (
    "🤱 *FIND NEARBY LACTATION ROOMS*\n\n"
    "Tap the button below to share your location and I'll show you the nearest rooms."
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
# "nursing" is handled separately below — it needs to send a ReplyKeyboardMarkup.

_ROUTES: dict[str, tuple[str, callable, str | None]] = {
    "menu":         (_WELCOME,        main_menu,          "Markdown"),
    "info":         (_INFO,           info_menu,          "Markdown"),
    "mentorship":   (_MENTORSHIP,     back_to_info,       "Markdown"),
    "health":       (_HEALTH,         health_menu,        "Markdown"),
    "ippt":         (_IPPT,           back_to_health,     "Markdown"),
    "bmi":          (_BMI,            back_to_health,     "Markdown"),
    "welfare":      (_WELFARE,        welfare_menu,       "Markdown"),
    "policies":     (_POLICIES,       policies_menu,      "Markdown"),
    "dress":        (_DRESS,          back_to_policies,   "Markdown"),
    "harassment":   (_HARASSMENT,     back_to_policies,   "Markdown"),
    "contact":      (_CONTACT,        contact_menu,       "Markdown"),
    "channel":      (_CHANNEL,        back_to_contact,    None),
    "email":        (_EMAIL,          back_to_contact,    None),
    "anon_feedback":(_ANON_FEEDBACK,  anon_feedback_menu, "Markdown"),
}


async def _cleanup_nursing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Delete any temporary nursing flow messages and remove the reply keyboard."""
    kb_msg_id = context.user_data.pop("nursing_kb_msg_id", None)
    if kb_msg_id:
        try:
            await context.bot.delete_message(chat_id, kb_msg_id)
        except Exception:
            pass
        # Send and immediately delete a silent ReplyKeyboardRemove to dismiss the keyboard
        try:
            rm = await context.bot.send_message(
                chat_id, "\u200b", reply_markup=ReplyKeyboardRemove()
            )
            await context.bot.delete_message(chat_id, rm.message_id)
        except Exception:
            pass

    nursing = context.user_data.pop("nursing_msgs", None)
    if nursing:
        for mid in nursing["delete"]:
            try:
                await context.bot.delete_message(nursing["chat_id"], mid)
            except Exception:
                pass


@rate_limit
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    try:
        await query.answer()
    except Exception as exc:
        logger.warning("Stale callback ignored: %s", exc)
        return

    chat_id = query.message.chat_id
    await _cleanup_nursing(context, chat_id)

    if query.data == "nursing":
        await safe_edit(query, _NURSING_PROMPT, nursing_back_menu(), "Markdown")
        kb_msg = await context.bot.send_message(
            chat_id,
            "📍 Tap the button below to share your location:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Share My Location", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )
        context.user_data["nursing_kb_msg_id"] = kb_msg.message_id
        return

    route = _ROUTES.get(query.data)
    if route is None:
        logger.warning("Unknown callback_data: %s", query.data)
        return

    text, keyboard_fn, parse_mode = route
    await safe_edit(query, text, keyboard_fn(), parse_mode)
