from telebot import types
import config

def create_main_menu_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("خدمات زيادة تفاعل سوشيال ميديا 🛍️", callback_data="show_services_menu")
    )
    if config.WEBAPP_URL:
        web_app_url = f"{config.WEBAPP_URL}/web/services.html"
        markup.add(
            types.InlineKeyboardButton("الخدمات 🌐", web_app=types.WebAppInfo(url=web_app_url))
        )
    markup.add(
        types.InlineKeyboardButton("شحن الرصيد 💸", callback_data="show_recharge_options"),
        types.InlineKeyboardButton("معلوماتي 🪪 ", callback_data="show_my_balance")
    )
    # My Orders button
    orders_button = types.InlineKeyboardButton("طلباتي 📋", callback_data="show_my_orders")
    if config.WEBAPP_URL:
        orders_web_app_url = f"{config.WEBAPP_URL}/web/orders.html"
        orders_button = types.InlineKeyboardButton("طلباتي 📋", web_app=types.WebAppInfo(url=orders_web_app_url))

    markup.add(
        orders_button,
        types.InlineKeyboardButton("ربح اموال مجانا 👥", callback_data="show_referral_system"),
    )
    markup.add(
        types.InlineKeyboardButton("تواصل معنا 📞", url=config.SUPPORT_CHANNEL_LINK)
    )
    return markup
