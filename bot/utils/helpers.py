import logging
from telegram import CallbackQuery, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def safe_edit(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = "Markdown",
) -> None:
    """Edit a message, silently ignoring harmless duplicate-edit errors."""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except Exception as exc:
        if "Message is not modified" in str(exc):
            return
        logger.warning("safe_edit error: %s", exc)
