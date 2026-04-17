from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import main_menu

WELCOME_TEXT = (
    "🚀 *RSAF WINGS DIGITAL ASSISTANT*\n"
    "Women INspiring Growth and Support\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "How can we support you today?\n"
    "━━━━━━━━━━━━━━━━━━"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )
