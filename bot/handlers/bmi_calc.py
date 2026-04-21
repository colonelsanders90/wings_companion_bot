"""
BMI calculator — 2-step ConversationHandler.

Flow:
  [callback: bmi_calc] → ASK_HEIGHT → ASK_WEIGHT → result
  Cancel at any step returns to the Health menu.
"""

from __future__ import annotations

import logging

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
ASK_HEIGHT, ASK_WEIGHT = range(2)

# ── Storage keys inside context.user_data ────────────────────────────────────
_KEY  = "bmi_calc"
_MSG  = "bmi_calc_msg_id"
_CHAT = "bmi_calc_chat_id"

# ── Back-button callback_data constants ──────────────────────────────────────
_BACK_HEIGHT = "bmi_back_height"   # from step 2 → step 1


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _step_kb(back_data: str | None = None) -> InlineKeyboardMarkup:
    row = []
    if back_data:
        row.append(InlineKeyboardButton("◀️ Back", callback_data=back_data))
    row.append(InlineKeyboardButton("❌ Cancel", callback_data="bmi_calc_cancel"))
    return InlineKeyboardMarkup([row])


def _result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit answers",    callback_data=_BACK_HEIGHT)],
        [InlineKeyboardButton("🔄 Calculate Again",  callback_data="bmi_calc")],
        [InlineKeyboardButton("◀️ Back to Health",   callback_data="health")],
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _delete_user_msg(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception:
        pass


async def _edit_prompt(
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
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


def _bmi_category(bmi: float) -> tuple[str, str]:
    """Return (category_label, advice_text). advice_text is empty if not warranted."""
    if bmi < 18.5:
        return "Underweight", ""
    elif bmi < 25.0:
        return "Normal Weight", (
            "Great work maintaining a healthy weight! Keep up your active lifestyle. 🌟"
        )
    elif bmi < 27.0:
        return "Overweight (Mild)", ""
    elif bmi < 30.0:
        return "Overweight (Moderate)", (
            "Consider joining your unit's fitness programmes or a national healthy lifestyle "
            "programme. If you have any underlying medical conditions, it's best to seek "
            "advice from your MO first. 🏃\u200d♀️"
        )
    elif bmi < 32.5:
        return "Obese", ""
    elif bmi < 40.0:
        return "Severely Obese", ""
    else:
        return "Very Severely Obese", ""


# ── Per-step prompt builders ──────────────────────────────────────────────────

def _height_text(data: dict, *, error: bool = False) -> str:
    prev = (
        f"\n_Previously entered: {data['height']:.2f} m — type the same to keep it_"
        if "height" in data else ""
    )
    if error:
        body = "Please enter a valid height in metres, e.g. `1.65`:\n_(Range: 1.00 – 2.50 m)_"
    else:
        body = f"What is your height in metres?{prev}\n_(e.g. `1.65` or `1.70`)_"
    return (
        "📐 *BMI CALCULATOR*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*Step 1 of 2 — Height*\n\n"
        f"{body}"
    )


def _weight_text(data: dict, *, error: bool = False) -> str:
    prev = (
        f"\n_Previously entered: {data['weight']:.1f} kg — type the same to keep it_"
        if "weight" in data else ""
    )
    if error:
        body = "Please enter a valid weight in kg, e.g. `65` or `65.5`:\n_(Range: 30 – 300 kg)_"
    else:
        body = f"What is your weight in kg?{prev}\n_(e.g. `65` or `65.5`)_"
    return (
        "📐 *BMI CALCULATOR*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Height: *{data['height']:.2f} m*\n\n"
        "*Step 2 of 2 — Weight*\n\n"
        f"{body}"
    )


def _build_result_text(data: dict) -> str:
    height   = data["height"]
    weight   = data["weight"]
    bmi      = weight / (height ** 2)
    category, advice = _bmi_category(bmi)
    advice_block = f"\n\n_{advice}_" if advice else ""

    pbf_block = (
        "\n\n📋 *Percentage Body Fat (PBF) Assessment*\n"
        "As your BMI is above 27, consider making an appointment with your Medical Centre "
        "to take a PBF measurement. The healthy threshold for servicewomen is *< 32%*."
    ) if bmi >= 27.0 else ""

    return (
        "📐 *BMI RESULT*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 Height: *{height:.2f} m*\n"
        f"⚖️ Weight: *{weight:.1f} kg*\n\n"
        f"📊 *BMI: {bmi:.1f}*\n"
        f"Category: *{category}*"
        f"{advice_block}"
        f"{pbf_block}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_BMI is a general screening tool. For personalised health advice, consult your MO._"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def bmi_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query: CallbackQuery = update.callback_query
    await query.answer()

    context.user_data[_KEY]  = {}
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id

    await query.edit_message_text(
        _height_text({}),
        parse_mode="Markdown",
        reply_markup=_step_kb(),
    )
    return ASK_HEIGHT


# ── Step handlers ─────────────────────────────────────────────────────────────

async def got_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw  = update.message.text.strip().replace(",", ".")
    data = context.user_data[_KEY]

    try:
        height = float(raw)
        if not (1.00 <= height <= 2.50):
            raise ValueError
    except ValueError:
        await _edit_prompt(context, _height_text(data, error=True), _step_kb())
        return ASK_HEIGHT

    data["height"] = height
    await _edit_prompt(context, _weight_text(data), _step_kb(_BACK_HEIGHT))
    return ASK_WEIGHT


async def got_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _delete_user_msg(update)
    raw  = update.message.text.strip().replace(",", ".")
    data = context.user_data[_KEY]

    try:
        weight = float(raw)
        if not (30.0 <= weight <= 300.0):
            raise ValueError
    except ValueError:
        await _edit_prompt(context, _weight_text(data, error=True), _step_kb(_BACK_HEIGHT))
        return ASK_WEIGHT

    data["weight"] = weight
    await _edit_prompt(context, _build_result_text(data), _result_kb())
    return ConversationHandler.END


# ── Back-navigation handler ───────────────────────────────────────────────────

async def back_to_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """◀️ Back from step 2 (weight) → step 1 (height), or re-entry via ✏️ Edit answers."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault(_KEY, {})
    context.user_data[_MSG]  = query.message.message_id
    context.user_data[_CHAT] = query.message.chat_id
    await _edit_prompt(context, _height_text(data), _step_kb())
    return ASK_HEIGHT


# ── Cancel ────────────────────────────────────────────────────────────────────

async def bmi_calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

def build_bmi_conv_handler() -> ConversationHandler:
    _cancel_cqh = CallbackQueryHandler(bmi_calc_cancel, pattern="^bmi_calc_cancel$")

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(bmi_calc_start,  pattern="^bmi_calc$"),
            # ✏️ Edit answers re-enters at step 1 with previous values as hints
            CallbackQueryHandler(back_to_height,  pattern=f"^{_BACK_HEIGHT}$"),
        ],
        states={
            ASK_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_height),
                _cancel_cqh,
            ],
            ASK_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_weight),
                CallbackQueryHandler(back_to_height, pattern=f"^{_BACK_HEIGHT}$"),
                _cancel_cqh,
            ],
        },
        fallbacks=[
            CommandHandler("cancel", bmi_calc_cancel),
            CallbackQueryHandler(bmi_calc_cancel, pattern="^(menu|health|bmi_calc_cancel)$"),
        ],
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
        allow_reentry=True,
    )
