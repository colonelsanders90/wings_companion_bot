"""
Interactive IPPT calculator — 4-step ConversationHandler for female servicewomen.

Flow:
  [callback: ippt_calc] → ASK_AGE → ASK_PUSHUPS → ASK_SITUPS → ASK_RUN → result
  At any step the user can tap ❌ Cancel to return to the Health menu.
"""

from __future__ import annotations

import logging
import re

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.utils.ippt_scoring import compute_score, fmt_seconds

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
ASK_AGE, ASK_PUSHUPS, ASK_SITUPS, ASK_RUN = range(4)

# ── Storage keys inside context.user_data ────────────────────────────────────
_KEY = "ippt_calc"          # sub-dict for all IPPT calc data
_MSG = "ippt_calc_msg_id"   # message_id of the bot's prompt message
_CHAT = "ippt_calc_chat_id"


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="ippt_calc_cancel")],
    ])


def _result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Calculate Again", callback_data="ippt_calc")],
        [InlineKeyboardButton("◀️ Back to Health",  callback_data="health")],
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _delete_user_msg(update: Update) -> None:
    """Silently delete the user's text message to keep the chat tidy."""
    try:
        await update.message.delete()
    except Exception:
        pass


async def _edit_prompt(
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """Edit the persistent bot prompt message in-place."""
    try:
        await context.bot.edit_message_text(
            chat_id=context.user_data[_CHAT],
            message_id=context.user_data[_MSG],
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception as exc:
        if "Message is not modified" not in str(exc):
            logger.warning("_edit_prompt error: %s", exc)


def _progress_bar(current: int, maximum: int, width: int = 10) -> str:
    """Return a simple text progress bar, e.g. ▓▓▓▓▓░░░░░ 50/100."""
    filled = round(width * current / maximum) if maximum else 0
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{maximum}"


def _build_result_text(data: dict) -> str:
    """Format the final results message."""
    score   = compute_score(data["age"], data["pushups"], data["situps"], data["run_secs"])
    run_fmt = fmt_seconds(data["run_secs"])

    award_line = score["award"]
    incentive  = f"  💰 Cash incentive: *{score['incentive']}*" if score["incentive"] else ""

    next_info = ""
    if score["next_award"]:
        next_name, pts_needed = score["next_award"]
        next_info = f"\n💡 *{pts_needed} more point{'s' if pts_needed != 1 else ''}* to reach {next_name}"

    total_bar  = _progress_bar(score["total"],      100)
    pu_bar     = _progress_bar(score["pushup_pts"],  25)
    su_bar     = _progress_bar(score["situp_pts"],   25)
    run_bar    = _progress_bar(score["run_pts"],     50)

    return (
        "🧮 *IPPT RESULT (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Age group: *{score['age_group']}*\n\n"
        "📊 *Station Breakdown*\n"
        f"  🤸 Push-ups ({data['pushups']} reps)\n"
        f"     {pu_bar}  *{score['pushup_pts']}/25 pts*\n\n"
        f"  💪 Sit-ups ({data['situps']} reps)\n"
        f"     {su_bar}  *{score['situp_pts']}/25 pts*\n\n"
        f"  🏃 2.4 km Run ({run_fmt})\n"
        f"     {run_bar}  *{score['run_pts']}/50 pts*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏅 *Total: {score['total']}/100*\n"
        f"     {total_bar}\n\n"
        f"*Award: {award_line}*{incentive}"
        f"{next_info}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_⚠️ Based on SAF 2015 IPPT format. "
        "Always verify with the official NS Portal._"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def ippt_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Triggered by the 'ippt_calc' inline button."""
    query: CallbackQuery = update.callback_query
    await query.answer()

    # Initialise / clear previous session data
    context.user_data[_KEY]  = {}
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id

    await query.edit_message_text(
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*Step 1 of 4 — Age*\n\n"
        "What is your age?\n"
        "_(Type a number between 18 and 60)_",
        parse_mode="Markdown",
        reply_markup=_cancel_kb(),
    )
    return ASK_AGE


# ── Step handlers ─────────────────────────────────────────────────────────────

async def got_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()

    try:
        age = int(raw)
        if not (18 <= age <= 60):
            raise ValueError
    except ValueError:
        await _edit_prompt(
            context,
            "🧮 *IPPT CALCULATOR (FEMALE)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "*Step 1 of 4 — Age*\n\n"
            "⚠️ Please enter a whole number between *18 and 60*:",
            _cancel_kb(),
        )
        return ASK_AGE

    context.user_data[_KEY]["age"] = age

    await _edit_prompt(
        context,
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{age}*\n\n"
        "*Step 2 of 4 — Push-ups (bent-knee)*\n\n"
        "How many push-ups did you complete?\n"
        "_(Type a number between 0 and 25)_",
        _cancel_kb(),
    )
    return ASK_PUSHUPS


async def got_pushups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()

    try:
        pushups = int(raw)
        if not (0 <= pushups <= 25):
            raise ValueError
    except ValueError:
        await _edit_prompt(
            context,
            "🧮 *IPPT CALCULATOR (FEMALE)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Age: *{context.user_data[_KEY]['age']}*\n\n"
            "*Step 2 of 4 — Push-ups (bent-knee)*\n\n"
            "⚠️ Please enter a whole number between *0 and 25*:",
            _cancel_kb(),
        )
        return ASK_PUSHUPS

    context.user_data[_KEY]["pushups"] = pushups
    age = context.user_data[_KEY]["age"]

    await _edit_prompt(
        context,
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{age}*\n"
        f"✅ Push-ups: *{pushups}*\n\n"
        "*Step 3 of 4 — Sit-ups*\n\n"
        "How many sit-ups did you complete?\n"
        "_(Type a number between 0 and 25)_",
        _cancel_kb(),
    )
    return ASK_SITUPS


async def got_situps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()

    try:
        situps = int(raw)
        if not (0 <= situps <= 25):
            raise ValueError
    except ValueError:
        data = context.user_data[_KEY]
        await _edit_prompt(
            context,
            "🧮 *IPPT CALCULATOR (FEMALE)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Age: *{data['age']}*\n"
            f"✅ Push-ups: *{data['pushups']}*\n\n"
            "*Step 3 of 4 — Sit-ups*\n\n"
            "⚠️ Please enter a whole number between *0 and 25*:",
            _cancel_kb(),
        )
        return ASK_SITUPS

    context.user_data[_KEY]["situps"] = situps
    data = context.user_data[_KEY]

    await _edit_prompt(
        context,
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{data['age']}*\n"
        f"✅ Push-ups: *{data['pushups']}*\n"
        f"✅ Sit-ups: *{situps}*\n\n"
        "*Step 4 of 4 — 2.4 km Run*\n\n"
        "What was your run time?\n"
        "_(Type in MM:SS format, e.g. `18:30`)_",
        _cancel_kb(),
    )
    return ASK_RUN


_RUN_RE = re.compile(r"^(\d{1,2}):([0-5]\d)$")


async def got_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()

    match = _RUN_RE.match(raw)
    if not match:
        data = context.user_data[_KEY]
        await _edit_prompt(
            context,
            "🧮 *IPPT CALCULATOR (FEMALE)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Age: *{data['age']}*\n"
            f"✅ Push-ups: *{data['pushups']}*\n"
            f"✅ Sit-ups: *{data['situps']}*\n\n"
            "*Step 4 of 4 — 2.4 km Run*\n\n"
            "⚠️ Please enter time in *MM:SS* format _(e.g. `18:30`)_:",
            _cancel_kb(),
        )
        return ASK_RUN

    minutes, seconds = int(match.group(1)), int(match.group(2))
    run_secs = minutes * 60 + seconds

    # Sanity check: must be between 13:00 (780s) and 40:00 (2400s)
    if not (600 <= run_secs <= 2400):
        data = context.user_data[_KEY]
        await _edit_prompt(
            context,
            "🧮 *IPPT CALCULATOR (FEMALE)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Age: *{data['age']}*\n"
            f"✅ Push-ups: *{data['pushups']}*\n"
            f"✅ Sit-ups: *{data['situps']}*\n\n"
            "*Step 4 of 4 — 2.4 km Run*\n\n"
            "⚠️ That time looks unusual. Please enter a realistic run time "
            "_(e.g. `18:30`)_:",
            _cancel_kb(),
        )
        return ASK_RUN

    context.user_data[_KEY]["run_secs"] = run_secs

    # Compute and display results
    result_text = _build_result_text(context.user_data[_KEY])
    await _edit_prompt(context, result_text, _result_kb())

    # Clean up stored data
    context.user_data.pop(_KEY,  None)
    context.user_data.pop(_MSG,  None)
    context.user_data.pop(_CHAT, None)

    return ConversationHandler.END


# ── Cancel ────────────────────────────────────────────────────────────────────

async def ippt_calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the ❌ Cancel inline button or /cancel command during the flow."""
    # Clean up stored data
    context.user_data.pop(_KEY,  None)
    context.user_data.pop(_MSG,  None)
    context.user_data.pop(_CHAT, None)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Return user to the Health menu by re-routing via callback_data="health"
        from bot.keyboards.menus import health_menu
        await query.edit_message_text(
            "💪 *HEALTH & FITNESS*\n\nSelect a topic:",
            parse_mode="Markdown",
            reply_markup=health_menu(),
        )
    elif update.message:
        await update.message.reply_text(
            "Calculator cancelled. Tap /start to return to the main menu."
        )

    return ConversationHandler.END


# ── ConversationHandler factory ───────────────────────────────────────────────

def build_ippt_conv_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ippt_calc_start, pattern="^ippt_calc$"),
        ],
        states={
            ASK_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_age),
                CallbackQueryHandler(ippt_calc_cancel, pattern="^ippt_calc_cancel$"),
            ],
            ASK_PUSHUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_pushups),
                CallbackQueryHandler(ippt_calc_cancel, pattern="^ippt_calc_cancel$"),
            ],
            ASK_SITUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_situps),
                CallbackQueryHandler(ippt_calc_cancel, pattern="^ippt_calc_cancel$"),
            ],
            ASK_RUN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_run),
                CallbackQueryHandler(ippt_calc_cancel, pattern="^ippt_calc_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", ippt_calc_cancel),
            # Allow navigating away via the main nav buttons without getting stuck
            CallbackQueryHandler(ippt_calc_cancel, pattern="^(menu|health|ippt_calc_cancel)$"),
        ],
        # Keep the conversation alive across bot restarts (polling mode)
        persistent=False,
        # Don't interfere with other conversations
        per_chat=True,
        per_user=True,
        per_message=False,
        # Allow re-entry (e.g. user taps "Calculate Again")
        allow_reentry=True,
    )
