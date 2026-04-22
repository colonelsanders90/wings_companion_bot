"""
Global error handler — registered with application.add_error_handler().

Catches all unhandled exceptions raised inside PTB handlers and:
  • Logs Conflict / NetworkError at WARNING (expected transient issues)
  • Logs everything else at ERROR with full traceback
  • Notifies the user with a friendly recovery message where possible
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.error import Conflict, NetworkError, TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error

    # ── Conflict (HTTP 409): duplicate polling instance ───────────────────────
    if isinstance(err, Conflict):
        logger.warning("Conflict — duplicate bot instance detected: %s", err)
        return

    # ── Transient network issues ──────────────────────────────────────────────
    if isinstance(err, NetworkError):
        logger.warning("Network error (transient): %s", err)
        return

    # ── All other Telegram API errors ────────────────────────────────────────
    if isinstance(err, TelegramError):
        logger.error("TelegramError in update %s: %s", update, err, exc_info=err)
    else:
        # Unexpected Python exception inside a handler
        logger.error("Unhandled exception for update %s", update, exc_info=err)

    # Best-effort: tell the user something went wrong
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong on my end. Please try again or tap /start to restart."
            )
        except Exception:
            pass
