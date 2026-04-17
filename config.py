import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "polling")

# Webhook — only used when DEPLOYMENT_MODE=webhook
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
