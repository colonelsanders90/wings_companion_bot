"""
AWS Lambda handler — receives Telegram webhook events via API Gateway.

Infrastructure sketch
─────────────────────
  Telegram  ──HTTPS──▶  API Gateway (POST /webhook)
                              │
                              ▼
                        Lambda (this file)
                              │
                         python-telegram-bot
                              │
                         Telegram API

Setup steps
───────────
1. Deploy this Lambda (zip or container image).
2. Set BOT_TOKEN in Lambda env vars (use Secrets Manager for production).
3. Create an API Gateway HTTP API → POST /webhook → this Lambda.
4. Register the webhook with Telegram:
     curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<APIGW_URL>/webhook&secret_token=<SECRET>"
"""

import asyncio
import json
import logging

from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

import config
from bot.handlers.callbacks import button
from bot.handlers.commands import start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build the application once at cold-start so it is reused across warm invocations.
_app = ApplicationBuilder().token(config.BOT_TOKEN).build()
_app.add_handler(CommandHandler("start", start))
_app.add_handler(CallbackQueryHandler(button))


def handler(event: dict, context) -> dict:
    """Lambda entry point — called by API Gateway for every incoming update."""

    # Validate the secret token header when configured
    if config.WEBHOOK_SECRET:
        headers = event.get("headers") or {}
        incoming = headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming != config.WEBHOOK_SECRET:
            logger.warning("Invalid secret token — request rejected")
            return {"statusCode": 403, "body": "Forbidden"}

    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    async def process():
        await _app.initialize()
        update = Update.de_json(body, _app.bot)
        await _app.process_update(update)

    asyncio.get_event_loop().run_until_complete(process())
    return {"statusCode": 200, "body": "ok"}
