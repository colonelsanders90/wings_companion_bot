"""
Per-user sliding-window rate limiter.

Protects all handlers from spam and accidental flooding.
Default: 10 requests per 30 seconds per user.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ── Tuneable constants ────────────────────────────────────────────────────────
MAX_CALLS: int = 10       # max requests allowed per user …
WINDOW_SECONDS: int = 30  # … within this rolling window (seconds)

# ── In-memory store: user_id → deque of monotonic timestamps ─────────────────
_timestamps: dict[int, deque[float]] = defaultdict(deque)


def _is_rate_limited(user_id: int) -> bool:
    """Return True (and do NOT record) if the user is over the limit, else record and return False."""
    now = time.monotonic()
    dq = _timestamps[user_id]

    # Evict entries that have fallen outside the window
    while dq and dq[0] < now - WINDOW_SECONDS:
        dq.popleft()

    if len(dq) >= MAX_CALLS:
        return True

    dq.append(now)
    return False


def rate_limit(func):
    """
    Decorator for any PTB handler coroutine (Update, ContextTypes.DEFAULT_TYPE).

    When a user exceeds the rate limit:
    - Callback queries → silently answered with a brief alert (no spinner stuck)
    - Messages        → replied with a friendly throttle notice
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            # System/channel updates — let them through
            return await func(update, context, *args, **kwargs)

        if _is_rate_limited(user.id):
            logger.warning("Rate limit exceeded — user_id=%d username=%s", user.id, user.username)

            if update.callback_query:
                try:
                    await update.callback_query.answer(
                        "⏳ You're going too fast! Please slow down.",
                        show_alert=False,
                    )
                except Exception:
                    pass
            elif update.message:
                try:
                    await update.message.reply_text("⏳ Please slow down a little.")
                except Exception:
                    pass
            return  # Drop the update — do NOT call the real handler

        return await func(update, context, *args, **kwargs)

    return wrapper
