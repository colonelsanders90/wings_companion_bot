"""
Interactive IPPT calculator — 4-step ConversationHandler for female servicewomen.

Flow:
  [callback: ippt_calc] → ASK_AGE ⇄ ASK_PUSHUPS ⇄ ASK_SITUPS ⇄ ASK_RUN → result
  Users can backtrack at any step to correct a previous entry.
  At any step the user can tap ❌ Cancel to return to the Health menu.
"""

from __future__ import annotations

import logging
import random
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
from bot.utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

# ── Encouraging quotes ────────────────────────────────────────────────────────
_QUOTES: list[str] = [
    "Every rep counts. Every second matters. Keep pushing! 💪",
    "Progress is progress, no matter how small. Be proud of yourself! 🌟",
    "The hardest part is showing up — and you did. 🙌",
    "Strong women lift each other up — and lift themselves too! 🏋️‍♀️",
    "Discipline today, strength tomorrow. You've got this! 🔥",
    "Your only competition is who you were yesterday. 🏅",
    "Sweat now, shine later. Keep going! ✨",
    "Fitness is not about being better than someone else — it's about being better than you used to be. 💫",
    "One run at a time. One rep at a time. One day at a time. 🌈",
    "Believe in yourself and all that you are. You are stronger than you think! 💖",
    "Great things never come from comfort zones. Push through! 🚀",
    "You train, you sweat, you improve. That's the WINGS spirit! 🦅",
    "Rest if you must, but don't you quit. 🛡️",
    "The body achieves what the mind believes. 🧠💪",
    "Champions aren't made in gyms — they're made from what they have inside. 🏆",
]

# ── Conversation states ───────────────────────────────────────────────────────
ASK_AGE, ASK_PUSHUPS, ASK_SITUPS, ASK_RUN = range(4)

# ── Storage keys inside context.user_data ────────────────────────────────────
_KEY  = "ippt_calc"          # sub-dict for all IPPT calc data
_MSG  = "ippt_calc_msg_id"   # message_id of the persistent bot prompt
_CHAT = "ippt_calc_chat_id"

# ── Back-button callback_data constants ──────────────────────────────────────
_BACK_AGE = "ippt_back_age"   # from step 2 → step 1
_BACK_PU  = "ippt_back_pu"    # from step 3 → step 2
_BACK_SU  = "ippt_back_su"    # from step 4 → step 3


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _step_kb(back_data: str | None = None) -> InlineKeyboardMarkup:
    """Build the per-step keyboard.  Pass back_data to add a ◀️ Back button."""
    row = []
    if back_data:
        row.append(InlineKeyboardButton("◀️ Back", callback_data=back_data))
    row.append(InlineKeyboardButton("❌ Cancel", callback_data="ippt_calc_cancel"))
    return InlineKeyboardMarkup([row])


def _result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit answers",   callback_data=_BACK_AGE)],
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


# ── Per-step prompt builders ─────────────────────────────────────────────────
# Each builder produces the full message text for that step.
# Pass error=True to show a validation error instead of the normal hint.

def _age_text(data: dict, *, error: bool = False) -> str:
    prev = f"\n_Previously entered: {data['age']} — type the same to keep it_" \
           if "age" in data else ""
    body = "⚠️ Please enter a whole number between *18 and 60*:" if error \
           else f"What is your age?{prev}\n_(Type a number between 18 and 60)_"
    return (
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*Step 1 of 4 — Age*\n\n"
        f"{body}"
    )


def _pu_text(data: dict, *, error: bool = False) -> str:
    prev = f"\n_Previously entered: {data['pushups']} — type the same to keep it_" \
           if "pushups" in data else ""
    body = "⚠️ Please enter a whole number between *0 and 60*:" if error \
           else f"How many push-ups did you complete?{prev}\n_(Type a number between 0 and 60)_"
    return (
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{data['age']}*\n\n"
        "*Step 2 of 4 — Push-ups (bent-knee)*\n\n"
        f"{body}"
    )


def _su_text(data: dict, *, error: bool = False) -> str:
    prev = f"\n_Previously entered: {data['situps']} — type the same to keep it_" \
           if "situps" in data else ""
    body = "⚠️ Please enter a whole number between *0 and 60*:" if error \
           else f"How many sit-ups did you complete?{prev}\n_(Type a number between 0 and 60)_"
    return (
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{data['age']}*\n"
        f"✅ Push-ups: *{data['pushups']}*\n\n"
        "*Step 3 of 4 — Sit-ups*\n\n"
        f"{body}"
    )


def _run_text(data: dict, *, error: bool = False) -> str:
    prev_fmt = fmt_seconds(data["run_secs"]) if "run_secs" in data else None
    prev = f"\n_Previously entered: {prev_fmt} — type the same to keep it_" \
           if prev_fmt else ""
    if error:
        body = "⚠️ Please enter time in *MM:SS* format _(e.g. `14:30`. Fastest: `08:00`)_:"
    else:
        body = (
            f"What was your 2.4 km run time?{prev}\n"
            "_(Type in MM:SS format, e.g. `14:30`. Fastest accepted: `08:00`)_"
        )
    return (
        "🧮 *IPPT CALCULATOR (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Age: *{data['age']}*\n"
        f"✅ Push-ups: *{data['pushups']}*\n"
        f"✅ Sit-ups: *{data['situps']}*\n\n"
        "*Step 4 of 4 — 2.4 km Run*\n\n"
        f"{body}"
    )


def _fmt_improvement(seconds: int) -> str:
    """Format a time improvement, e.g. 10 → '10s', 70 → '1:10'."""
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _build_result_text(data: dict) -> str:
    """Format the final results message."""
    score   = compute_score(data["age"], data["pushups"], data["situps"], data["run_secs"])
    run_fmt = fmt_seconds(data["run_secs"])

    incentive = f"  💰 Cash incentive: *{score['incentive']}*" if score["incentive"] else ""

    next_info = ""
    if score["next_award"]:
        next_name, pts_needed = score["next_award"]
        next_info = f"\n💡 *{pts_needed} more point{'s' if pts_needed != 1 else ''}* to reach {next_name}"

    total_bar = _progress_bar(score["total"],      100)
    pu_bar    = _progress_bar(score["pushup_pts"],  25)
    su_bar    = _progress_bar(score["situp_pts"],   25)
    run_bar   = _progress_bar(score["run_pts"],     50)

    # "how close to +1 pt?" hints — blank string when already at max
    n = score["pu_next_reps"]
    pu_hint = f"\n     _+{n} rep{'s' if n != 1 else ''} → +1 pt_" if n else ""

    n = score["su_next_reps"]
    su_hint = f"\n     _+{n} rep{'s' if n != 1 else ''} → +1 pt_" if n else ""

    n = score["run_next_secs"]
    run_hint = f"\n     _{_fmt_improvement(n)} faster → +1 pt_" if n else ""

    quote = random.choice(_QUOTES)

    return (
        "🧮 *IPPT RESULT (FEMALE)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Age group: *{score['age_group']}*\n\n"
        "📊 *Station Breakdown*\n"
        f"  🤸 Push-ups ({data['pushups']} reps)\n"
        f"     {pu_bar}  *{score['pushup_pts']}/25 pts*{pu_hint}\n\n"
        f"  💪 Sit-ups ({data['situps']} reps)\n"
        f"     {su_bar}  *{score['situp_pts']}/25 pts*{su_hint}\n\n"
        f"  🏃 2.4 km Run ({run_fmt})\n"
        f"     {run_bar}  *{score['run_pts']}/50 pts*{run_hint}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏅 *Total: {score['total']}/100*\n"
        f"     {total_bar}\n\n"
        f"*Award: {score['award']}*{incentive}"
        f"{next_info}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"_{quote}_\n\n"
        "_⚠️ Based on SAF 2015 IPPT format. "
        "Always verify with the official NS Portal._"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

@rate_limit
async def ippt_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Triggered by the 'ippt_calc' inline button."""
    query: CallbackQuery = update.callback_query
    await query.answer()

    context.user_data[_KEY]  = {}   # fresh session — wipe any previous run data
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id

    await query.edit_message_text(
        _age_text({}),
        parse_mode="Markdown",
        reply_markup=_step_kb(),
    )
    return ASK_AGE


# ── Forward step handlers ─────────────────────────────────────────────────────

async def got_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()
    data = context.user_data[_KEY]

    try:
        age = int(raw)
        if not (18 <= age <= 60):
            raise ValueError
    except ValueError:
        await _edit_prompt(context, _age_text(data, error=True), _step_kb())
        return ASK_AGE

    data["age"] = age
    await _edit_prompt(context, _pu_text(data), _step_kb(_BACK_AGE))
    return ASK_PUSHUPS


async def got_pushups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()
    data = context.user_data[_KEY]

    try:
        pushups = int(raw)
        if not (0 <= pushups <= 60):
            raise ValueError
    except ValueError:
        await _edit_prompt(context, _pu_text(data, error=True), _step_kb(_BACK_AGE))
        return ASK_PUSHUPS

    data["pushups"] = pushups
    await _edit_prompt(context, _su_text(data), _step_kb(_BACK_PU))
    return ASK_SITUPS


async def got_situps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()
    data = context.user_data[_KEY]

    try:
        situps = int(raw)
        if not (0 <= situps <= 60):
            raise ValueError
    except ValueError:
        await _edit_prompt(context, _su_text(data, error=True), _step_kb(_BACK_PU))
        return ASK_SITUPS

    data["situps"] = situps
    await _edit_prompt(context, _run_text(data), _step_kb(_BACK_SU))
    return ASK_RUN


_RUN_RE = re.compile(r"^(\d{1,2}):([0-5]\d)$")


async def got_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw = update.message.text.strip()
    data = context.user_data[_KEY]

    match = _RUN_RE.match(raw)
    if not match:
        await _edit_prompt(context, _run_text(data, error=True), _step_kb(_BACK_SU))
        return ASK_RUN

    minutes, seconds = int(match.group(1)), int(match.group(2))
    run_secs = minutes * 60 + seconds

    if not (480 <= run_secs <= 2400):
        await _edit_prompt(context, _run_text(data, error=True), _step_kb(_BACK_SU))
        return ASK_RUN

    data["run_secs"] = run_secs

    # Edit the persistent bot prompt in-place with the results.
    # Keep _KEY / _MSG / _CHAT alive so ✏️ Edit answers can restore hints
    # when the user re-enters the conversation via back_to_age.
    await _edit_prompt(context, _build_result_text(data), _result_kb())

    return ConversationHandler.END


# ── Back-navigation handlers ──────────────────────────────────────────────────

async def back_to_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """◀️ Back from step 2 (push-ups) → step 1 (age)."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault(_KEY, {})
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id
    await _edit_prompt(context, _age_text(data), _step_kb())
    return ASK_AGE


async def back_to_pushups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """◀️ Back from step 3 (sit-ups) → step 2 (push-ups)."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault(_KEY, {})
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id
    await _edit_prompt(context, _pu_text(data), _step_kb(_BACK_AGE))
    return ASK_PUSHUPS


async def back_to_situps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """◀️ Back from step 4 (run) → step 3 (sit-ups)."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault(_KEY, {})
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id
    await _edit_prompt(context, _su_text(data), _step_kb(_BACK_PU))
    return ASK_SITUPS


# ── Cancel ────────────────────────────────────────────────────────────────────

async def ippt_calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the ❌ Cancel inline button or /cancel command during the flow."""
    context.user_data.pop(_KEY,  None)
    context.user_data.pop(_MSG,  None)
    context.user_data.pop(_CHAT, None)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
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
    _cancel_cqh = CallbackQueryHandler(ippt_calc_cancel, pattern="^ippt_calc_cancel$")

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ippt_calc_start,  pattern="^ippt_calc$"),
            # ✏️ Edit answers re-enters at step 1 with previous values as hints
            CallbackQueryHandler(back_to_age,      pattern=f"^{_BACK_AGE}$"),
        ],
        states={
            ASK_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_age),
                _cancel_cqh,
            ],
            ASK_PUSHUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_pushups),
                CallbackQueryHandler(back_to_age,      pattern=f"^{_BACK_AGE}$"),
                _cancel_cqh,
            ],
            ASK_SITUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_situps),
                CallbackQueryHandler(back_to_pushups,  pattern=f"^{_BACK_PU}$"),
                _cancel_cqh,
            ],
            ASK_RUN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_run),
                CallbackQueryHandler(back_to_situps,   pattern=f"^{_BACK_SU}$"),
                _cancel_cqh,
            ],
        },
        fallbacks=[
            CommandHandler("cancel", ippt_calc_cancel),
            CallbackQueryHandler(ippt_calc_cancel, pattern="^(menu|health|ippt_calc_cancel)$"),
        ],
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
        allow_reentry=True,
    )
