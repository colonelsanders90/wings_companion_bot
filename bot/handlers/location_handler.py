import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from bot.data.lactation_rooms import LACTATION_ROOMS
from bot.utils.location import nearest_rooms

logger = logging.getLogger(__name__)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = update.message.location
    results = nearest_rooms(loc.latitude, loc.longitude, LACTATION_ROOMS, n=5)

    lines = ["🤱 *NEAREST LACTATION ROOMS*\n"]
    for i, (dist_km, room) in enumerate(results, 1):
        dist_str = f"{dist_km * 1000:.0f} m" if dist_km < 1 else f"{dist_km:.1f} km"
        lines.append(
            f"*{i}. {room['name']}*\n"
            f"📍 {room['building']}, {room['floor']}\n"
            f"🕐 {room['hours']}\n"
            f"📏 {dist_str} away\n"
        )

    lines.append("_Type /start to return to the main menu._")

    context.user_data.pop("awaiting_nursing_location", None)

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
