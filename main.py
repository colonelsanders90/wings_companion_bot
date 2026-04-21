"""
Entry point — supports both polling (Railway / local) and webhook (AWS) modes.

  DEPLOYMENT_MODE=polling   → long-polling, no public URL needed
  DEPLOYMENT_MODE=webhook   → starts a local HTTPS listener; put behind
                              an ALB or API Gateway for AWS Lambda-less deploys,
                              or use lambda_handler.py for true Lambda.
"""

import logging

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import config
from bot.handlers.callbacks import button
from bot.handlers.bmi_calc import build_bmi_conv_handler
from bot.handlers.commands import start
from bot.handlers.ippt_calc import build_ippt_conv_handler
from bot.handlers.location_handler import handle_location

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # ConversationHandler must be registered BEFORE the catch-all CallbackQueryHandler
    app.add_handler(build_ippt_conv_handler())
    app.add_handler(build_bmi_conv_handler())
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    return app


def run_polling():
    logger.info("Starting bot in POLLING mode")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


def run_webhook():
    logger.info("Starting bot in WEBHOOK mode on port %s", config.WEBHOOK_PORT)
    app = build_app()
    app.run_webhook(
        listen="0.0.0.0",
        port=config.WEBHOOK_PORT,
        webhook_url=config.WEBHOOK_URL,
        secret_token=config.WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    if config.DEPLOYMENT_MODE == "webhook":
        run_webhook()
    else:
        run_polling()
