from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import main_menu

WELCOME_TEXT = (
    "Dear servicewomen,\n\n"
    "It is with great pride and warmth that I welcome you to the *RSAF WINGS Companion Bot*.\n\n"
    "WINGS — _Women INspiring Growth and Support_ — exists because each of you matters. "
    "Whether you are just beginning your journey in the RSAF, navigating the demands of service life, "
    "or looking to grow further in your career, you deserve a space where support is always within reach.\n\n"
    "This bot was built with you in mind. At any hour of the day, it is here to guide you — "
    "to the right information, the right people, and the right channels — so that no question goes "
    "unanswered and no concern goes unheard.\n\n"
    "You are not alone. The WINGS community stands behind you, and I personally stand behind every one of you.\n\n"
    "Warmly,\n"
    "*COL Lee Mei Yi*\n"
    "Head, RSAF WINGS\n\n"
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
