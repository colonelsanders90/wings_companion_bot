import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from bot.data.lactation_rooms import LACTATION_ROOMS
from bot.utils.location import nearest_rooms

logger = logging.getLogger(__name__)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = update.message.location
    results = nearest_rooms(loc.latitude, loc.longitude, LACTATION_ROOMS, n=5)

    context.user_data.pop("awaiting_nursing_location", None)

    # Summary text — also dismisses the reply keyboard
    lines = ["🤱 *NEAREST LACTATION ROOMS*\n"]
    for i, (dist_km, room) in enumerate(results, 1):
        dist_str = f"{dist_km * 1000:.0f} m" if dist_km < 1 else f"{dist_km:.1f} km"
        lines.append(f"*{i}.* {room['name']} — _{dist_str}_")
    lines.append("\n_Tap a venue below to view on the map and navigate._")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Venue cards with map thumbnail + navigation button
    for i, (dist_km, room) in enumerate(results):
        dist_str = f"{dist_km * 1000:.0f} m" if dist_km < 1 else f"{dist_km:.1f} km"
        maps_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={loc.latitude},{loc.longitude}"
            f"&destination={room['lat']},{room['lng']}"
        )

        is_last = i == len(results) - 1
        buttons = [[InlineKeyboardButton("🗺️ Navigate", url=maps_url)]]
        if is_last:
            buttons.append([InlineKeyboardButton("◀️ Back to Start", callback_data="menu")])

        await context.bot.send_venue(
            update.message.chat_id,
            latitude=room["lat"],
            longitude=room["lng"],
            title=room["name"],
            address=f"{room['building']}, {room['floor']} · {room['hours']} · {dist_str} away",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
