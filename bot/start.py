import traceback
from telebot import types
from . import bot, user_states
from database import Session, User, Service
from utils import get_or_create_user
from utils import send_message_to_user
from config import START_MESSAGE, ADMIN_IDS, SUPPORT_CHANNEL_LINK
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
    markup.add(
        types.InlineKeyboardButton("طلباتي 📋", callback_data="show_my_orders"),
        types.InlineKeyboardButton("ربح اموال مجانا 👥", callback_data="show_referral_system"),
    )
    markup.add(
        types.InlineKeyboardButton("تواصل معنا 📞", url=config.SUPPORT_CHANNEL_LINK)
    )
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        chat_id = message.chat.id
        telegram_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name

        referrer_id = None
        start_payload = None
        s = Session()
        try:
            if message.text and len(message.text.split()) > 1:
                start_payload = message.text.split()[1]
                if start_payload.startswith('service_'):
                    service_id = int(start_payload.split('_')[1])

                    user, is_new_user = get_or_create_user(telegram_id, username, full_name, session=s)

                    service = s.query(Service).get(service_id)

                    if not service or not service.is_available:
                        bot.send_message(chat_id, "الخدمة المطلوبة غير متاحة حاليًا أو غير موجودة.", parse_mode="HTML")
                        sent_message = bot.send_message(chat_id, f"{START_MESSAGE}\n\n<blockquote><b>معرفك:</b> <code>{user.telegram_id}</code></blockquote>\n<blockquote><b>رصيدك:</b> ${user.balance:.2f}</blockquote>\n<b>اختر من الأزرار :</b>",
                                                        reply_markup=create_main_menu_inline_keyboard(), parse_mode="HTML")
                        user_states[chat_id] = {"main_menu_message_id": sent_message.message_id}
                        s.close()
                        return

                    user_states[chat_id] = {"state": "waiting_quantity", "service_id": service_id, "message_id": message.message_id}

                    service_details_text = (
                        f"<b>تفاصيل الخدمة:</b>\n"
                        f"<blockquote>✨ <b>الاسم:</b> {service.name}</blockquote>\n"
                        f"<blockquote>📝 <b>الوصف:</b> {service.description or 'لا يوجد وصف.'}</blockquote>\n"
                        f"<blockquote>💲 <b>السعر:</b> ${service.base_price:.2f} لكل {service.base_quantity}</blockquote>\n"
                        f"<blockquote>🔢 <b>الحد الأدنى للكمية:</b> {service.min_quantity}</blockquote>\n"
                        f"<blockquote>🔢 <b>الحد الأقصى للكمية:</b> {service.max_quantity}</blockquote>\n\n"
                        f" إدخل الكمية المطلوبة (مثال: {service.base_quantity}):"
                    )

                    back_button_data = f"cat_{service.category_id}"
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔙 رجوع إلى التصنيف", callback_data=back_button_data))

                    sent_message = bot.send_message(chat_id, service_details_text, reply_markup=markup, parse_mode="HTML")
                    user_states[chat_id]["message_id"] = sent_message.message_id
                    s.close()
                    return

                else:
                    referral_code = start_payload
                    referrer = s.query(User).filter_by(referral_code=referral_code).first()
                    if referrer:
                        referrer_id = referrer.telegram_id

            user, is_new_user = get_or_create_user(telegram_id, username, full_name, referrer_id, session=s)

            welcome_message_text = (
                f"{START_MESSAGE}\n\n"
                f"<blockquote><b>معرفك:</b> <code>{user.telegram_id}</code></blockquote>\n"
                f"<blockquote><b>رصيدك:</b> ${user.balance:.2f}</blockquote>\n"
                f"<b>اختر من الأزرار :</b>"
            )

            sent_message = bot.send_message(chat_id, welcome_message_text,
                                            reply_markup=create_main_menu_inline_keyboard(),
                                            parse_mode="HTML")
            user_states[chat_id] = {"main_menu_message_id": sent_message.message_id}

            if is_new_user:
                admin_message = (
                    f"<blockquote>👤 <b>مستخدم جديد انضم إلى البوت!</b></blockquote>\n\n"
                    f"<blockquote>🆔 <b>المعرف:</b> <code>{user.telegram_id}</code></blockquote>\n"
                    f"<blockquote>👤 <b>الاسم:</b> {user.full_name}</blockquote>\n"
                    f"<blockquote>📌 <b>اليوزر:</b> "
                    f"{'@' + user.username if user.username else 'لا يوجد'}</blockquote>\n"
                    f"<blockquote>📅 <b>تاريخ التسجيل:</b> {user.registered_at.strftime('%Y-%m-%d %H:%M:%S')}</blockquote>\n"
                    f"<blockquote>🔗 <b>كود الإحالة:</b> <code>{user.referral_code}</code></blockquote>"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        send_message_to_user(
                            admin_id,
                            admin_message,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"فشل إرسال رسالة المستخدم الجديد للمشرف {admin_id}: {e}")

            if user.is_admin:
                admin_markup = types.InlineKeyboardMarkup()
                admin_markup.add(types.InlineKeyboardButton("لوحة تحكم المشرف ⚙️", callback_data="show_admin_panel_info"))
                bot.send_message(chat_id, "لوحة الادمن سيتم اتعديل لاحقا", reply_markup=admin_markup, parse_mode="HTML")
        except Exception as e:
            print(f"خطأ في معالج /start: {e}")
            bot.send_message(chat_id, "حدث خطأ أثناء بدء البوت. يرجى المحاولة مرة أخرى لاحقًا.")
        finally:
            s.close()
    except Exception as e:
        print(f"خطأ في handle_start: {e}\n{traceback.format_exc()}")
        bot.send_message(message.chat.id, "حدث خطأ أثناء بدء البوت. يرجى المحاولة مرة أخرى.")
