from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 RSAF WINGS Information",  callback_data="info")],
        [InlineKeyboardButton("💪 Health & Fitness",        callback_data="health")],
        [InlineKeyboardButton("🤱 Welfare & Support",       callback_data="welfare")],
        [InlineKeyboardButton("📋 Policies & Guidelines",   callback_data="policies")],
        [InlineKeyboardButton("📲 Contact & Channels",      callback_data="contact")],
    ])


def info_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌱 Mentorship Programmes",  callback_data="mentorship")],
        [InlineKeyboardButton("🔗 Mentorship Sign-Up",
                              url="https://go.gov.sg/rsafwingsmentorshipsignup")],
        [InlineKeyboardButton("◀️ Back",                   callback_data="menu")],
    ])


def health_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏃 IPPT Standards",         callback_data="ippt")],
        [InlineKeyboardButton("◀️ Back",                   callback_data="menu")],
    ])


def welfare_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤱 Nursing Room Finder",    callback_data="nursing")],
        [InlineKeyboardButton("◀️ Back",                   callback_data="menu")],
    ])


def policies_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Dress Code",              callback_data="dress")],
        [InlineKeyboardButton("⚠️ Harassment & Misconduct", callback_data="harassment")],
        [InlineKeyboardButton("◀️ Back",                    callback_data="menu")],
    ])


def contact_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Telegram Channel",    callback_data="channel")],
        [InlineKeyboardButton("📧 OSN Email",           callback_data="email")],
        [InlineKeyboardButton("📝 Anonymous Feedback",  callback_data="anon_feedback")],
        [InlineKeyboardButton("◀️ Back",                callback_data="menu")],
    ])


def anon_feedback_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Open Form",
                              url="https://go.gov.sg/rsafwingsanonymousfeedback")],
        [InlineKeyboardButton("◀️ Back", callback_data="contact")],
    ])


def nursing_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back", callback_data="welfare")],
    ])


def back_to_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Start", callback_data="menu")],
    ])
