"""Central config loaded from environment / .env file."""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name, default=None, required=False):
    val = os.getenv(name, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val


# Budget
MONTHLY_BUDGET = float(_get("MONTHLY_BUDGET", "10000"))
CURRENCY = _get("CURRENCY", "INR")

# Telegram
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", required=True)
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID", required=True)

# Server
WEBHOOK_SECRET = _get("WEBHOOK_SECRET", required=True)
PORT = int(_get("PORT", "5000"))

DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")
