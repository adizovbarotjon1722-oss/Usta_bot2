from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": {
        "choose_language": "Tilni tanlang:",
        "welcome_back": "Xush kelibsiz, {name}!",
        "ask_name": "Assalomu alaykum! Ro'yxatdan o'tamiz.\nIsmingizni kiriting:",
        "ask_phone": "Telefon raqamingizni yuboring:",
        "phone_button": "📱 Raqamni yuborish",
        "registered": "Ro'yxatdan muvaffaqiyatli o'tdingiz!",
        "referral_applied": "Siz {name} taklifi bilan qo'shildingiz!",
        "invalid_phone": "Iltimos, tugma orqali telefon raqamingizni yuboring.",
        "menu_taxi": "🚗 Taksi",
        "menu_delivery": "📦 Yetkazib berish",
        "menu_open_route": "🧭 Ochiq marshrut",
        "open_route_intro": (
            "Ochiq marshrutda aniq manzilni oldindan aytish shart emas - yo'l davomida "
            "haydovchiga o'zingiz yo'l ko'rsatasiz. Narx safar davomiyligiga qarab hisoblanadi."
        ),
        "open_route_ask_pickup": "Qayerdan boshlaymiz?",
        "open_route_confirm": (
            "Boshlanish nuqtasi: {pickup}\nBoshlang'ich narx: {base_price} so'm "
            "(+ har daqiqaga {per_minute} so'm)\n\nTasdiqlaysizmi? (ha / yo'q)"
        ),
        "open_route_created": (
            "Buyurtmangiz qabul qilindi! Haydovchi qidirilmoqda...\n"
            "Yo'l davomida haydovchiga qayerga borishni o'zingiz aytib borasiz."
        ),
        "menu_orders": "📋 Buyurtmalarim",
        "menu_referral": "🎁 Do'stni taklif qilish",
        "ask_pickup": "Qayerdan olib ketishimiz kerak? (manzilni yozing)",
        "ask_dropoff": "Qayerga borishingiz kerak?",
        "ask_items": "Nima yetkazib berish kerak? (mahsulot nomini yozing)",
        "choose_store": "Qaysi nuqtadan yetkazib berishni tanlang:",
        "ask_delivery_address": (
            "Qayerga yetkazib berish kerak?\nAniq narx uchun joylashuvingizni yuboring, "
            "yoki manzilni qo'lda yozing:"
        ),
        "loc_or_text": "📍 Joylashuvni yuborish (aniq narx)",
        "type_address_button": "✍️ Manzilni yozish",
        "type_address_prompt": "Manzilni yozing:",
        "ask_when": "Buyurtmani hozir bersammi yoki keyinroqqa rejalashtirsammi?",
        "when_now": "🕐 Hozir",
        "when_later": "📅 Keyinroq",
        "ask_schedule_time": (
            "Qaysi sana va soatga rejalashtiramiz?\n"
            "Shu formatda yozing: KUN.OY.YIL SOAT:DAQIQA (masalan: 16.09.2026 08:00)"
        ),
        "schedule_invalid": "Format noto'g'ri. Masalan: 16.09.2026 08:00 shaklida yozing.",
        "schedule_past": "Bu vaqt allaqachon o'tib ketgan. Kelajakdagi vaqtni kiriting.",
        "scheduled_confirmed": "Buyurtmangiz {when} ga rejalashtirildi. O'sha vaqtda haydovchi qidiriladi.",
        "scheduled_dispatching": "Rejalashtirilgan buyurtmangiz #{order_id} uchun haydovchi qidirilmoqda...",
        "taxi_confirm": (
            "Qabul: {pickup}\nManzil: {dropoff}\n{distance_line}Narx: {price} so'm\n\n"
            "Promo-kodingiz bo'lsa yozing, aks holda tasdiqlash uchun \"ha\" deb yozing (bekor qilish uchun \"yo'q\"):"
        ),
        "delivery_confirm": (
            "Mahsulot: {items}\nManzil: {dropoff}\n{distance_line}Narx: {price} so'm\n\n"
            "Promo-kodingiz bo'lsa yozing, aks holda tasdiqlash uchun \"ha\" deb yozing (bekor qilish uchun \"yo'q\"):"
        ),
        "promo_applied": "Promo-kod qo'llanildi! Yangilangan narx: {price} so'm. Tasdiqlash uchun \"ha\" deb yozing.",
        "promo_invalid": "Bu promo-kod yaroqsiz yoki muddati tugagan. Qayta urinib ko'ring yoki \"ha\"/\"yo'q\" deb yozing.",
        "bonus_applied": " (shundan {bonus} so'm bonus hisobidan)",
        "order_created_taxi": "Buyurtmangiz qabul qilindi! Haydovchi qidirilmoqda...",
        "order_created_delivery": "Buyurtmangiz qabul qilindi! Kuryer qidirilmoqda...",
        "order_cancelled": "Buyurtma bekor qilindi.",
        "no_orders": "Hali buyurtmalaringiz yo'q.",
        "rate_prompt": "Iltimos, 1 dan 5 gacha raqam yuboring.",
        "rate_thanks": "Rahmat! Bahoyingiz saqlandi.",
        "pay_prompt": (
            "Agar onlayn to'lashni xohlasangiz, tugmalardan birini tanlang.\n"
            "Aks holda haydovchiga naqd to'lashingiz mumkin."
        ),
        "pay_payme": "💳 Payme orqali to'lash",
        "pay_click": "💳 Click orqali to'lash",
        "sos_button": "🆘 SOS",
        "sos_sent": "SOS signali yuborildi! Administrator xabardor qilindi.",
        "cancel_restricted": (
            "So'nggi {hours} soat ichida buyurtmalarni juda ko'p bekor qildingiz. "
            "Biroz kuting va qaytadan urinib ko'ring."
        ),
        "account_blocked": "Hisobingiz administrator tomonidan bloklangan. Savol bo'lsa, bog'laning.",
        "first_order_discount_applied": "🎁 Bu birinchi buyurtmangiz - {percent}% chegirma qo'llanildi!",
        "order_cancelled_by_user": "Buyurtma #{order_id} bekor qilindi.",
        "cancel_own_button": "❌ #{order_id} bekor qilish",
        "order_accepted_enroute": "Buyurtmangiz #{order_id} qabul qilindi! Haydovchi yo'lda.",
        "driver_arrived": "Haydovchi yetib keldi!",
        "order_completed_rate": (
            "Buyurtmangiz #{order_id} yakunlandi!\nNarxi: {price} so'm\n"
            "Haydovchini baholang: 1 dan 5 gacha raqam yuboring."
        ),
        "referral_info": (
            "Sizning taklif havolangiz:\n{link}\n\n"
            "Do'stingiz shu havola orqali qo'shilsa va birinchi buyurtmasini yakunlasa, "
            "sizga {bonus} so'm bonus tushadi.\n\n"
            "Joriy bonus balansingiz: {balance} so'm"
        ),
    },
    "ru": {
        "choose_language": "Выберите язык:",
        "welcome_back": "Добро пожаловать, {name}!",
        "ask_name": "Здравствуйте! Давайте зарегистрируемся.\nВведите ваше имя:",
        "ask_phone": "Отправьте ваш номер телефона:",
        "phone_button": "📱 Отправить номер",
        "registered": "Вы успешно зарегистрированы!",
        "referral_applied": "Вы присоединились по приглашению {name}!",
        "invalid_phone": "Пожалуйста, отправьте номер через кнопку.",
        "menu_taxi": "🚗 Такси",
        "menu_delivery": "📦 Доставка",
        "menu_open_route": "🧭 Открытый маршрут",
        "open_route_intro": (
            "В открытом маршруте не нужно заранее указывать точный адрес - вы сами "
            "будете направлять водителя в пути. Цена рассчитывается по времени поездки."
        ),
        "open_route_ask_pickup": "Откуда начнём?",
        "open_route_confirm": (
            "Точка начала: {pickup}\nНачальная цена: {base_price} сум "
            "(+ {per_minute} сум за каждую минуту)\n\nПодтверждаете? (да / нет)"
        ),
        "open_route_created": (
            "Ваш заказ принят! Ищем водителя...\n"
            "В пути вы сами будете указывать водителю куда ехать."
        ),
        "menu_orders": "📋 Мои заказы",
        "menu_referral": "🎁 Пригласить друга",
        "ask_pickup": "Откуда забрать? (напишите адрес)",
        "ask_dropoff": "Куда едем?",
        "ask_items": "Что нужно доставить? (напишите название товара)",
        "choose_store": "Выберите пункт, откуда доставить:",
        "ask_delivery_address": (
            "Куда доставить?\nДля точной цены отправьте геолокацию, "
            "или напишите адрес вручную:"
        ),
        "loc_or_text": "📍 Отправить геолокацию (точная цена)",
        "type_address_button": "✍️ Написать адрес",
        "type_address_prompt": "Напишите адрес:",
        "ask_when": "Оформить заказ сейчас или запланировать на потом?",
        "when_now": "🕐 Сейчас",
        "when_later": "📅 Позже",
        "ask_schedule_time": (
            "На какую дату и время запланировать?\n"
            "Напишите в формате: ДЕНЬ.МЕСЯЦ.ГОД ЧАС:МИНУТА (например: 16.09.2026 08:00)"
        ),
        "schedule_invalid": "Неверный формат. Например: 16.09.2026 08:00.",
        "schedule_past": "Это время уже прошло. Укажите время в будущем.",
        "scheduled_confirmed": "Ваш заказ запланирован на {when}. Водитель будет найден к этому времени.",
        "scheduled_dispatching": "Ищем водителя для вашего запланированного заказа #{order_id}...",
        "taxi_confirm": (
            "Откуда: {pickup}\nКуда: {dropoff}\n{distance_line}Цена: {price} сум\n\n"
            "Если есть промо-код, напишите его, иначе напишите \"да\" для подтверждения (\"нет\" для отмены):"
        ),
        "delivery_confirm": (
            "Товар: {items}\nАдрес: {dropoff}\n{distance_line}Цена: {price} сум\n\n"
            "Если есть промо-код, напишите его, иначе напишите \"да\" для подтверждения (\"нет\" для отмены):"
        ),
        "promo_applied": "Промо-код применён! Новая цена: {price} сум. Напишите \"да\" для подтверждения.",
        "promo_invalid": "Промо-код недействителен или истёк. Попробуйте снова или напишите \"да\"/\"нет\".",
        "bonus_applied": " (из них {bonus} сум из бонуса)",
        "order_created_taxi": "Ваш заказ принят! Ищем водителя...",
        "order_created_delivery": "Ваш заказ принят! Ищем курьера...",
        "order_cancelled": "Заказ отменён.",
        "no_orders": "У вас пока нет заказов.",
        "rate_prompt": "Пожалуйста, отправьте число от 1 до 5.",
        "rate_thanks": "Спасибо! Ваша оценка сохранена.",
        "pay_prompt": (
            "Если хотите оплатить онлайн, выберите один из вариантов.\n"
            "Либо оплатите водителю наличными."
        ),
        "pay_payme": "💳 Оплатить через Payme",
        "pay_click": "💳 Оплатить через Click",
        "sos_button": "🆘 SOS",
        "sos_sent": "Сигнал SOS отправлен! Администратор уведомлён.",
        "cancel_restricted": (
            "За последние {hours} часов вы слишком часто отменяли заказы. "
            "Подождите немного и попробуйте снова."
        ),
        "account_blocked": "Ваш аккаунт заблокирован администратором. Если есть вопросы, свяжитесь с нами.",
        "first_order_discount_applied": "🎁 Это ваш первый заказ - применена скидка {percent}%!",
        "order_cancelled_by_user": "Заказ #{order_id} отменён.",
        "cancel_own_button": "❌ Отменить #{order_id}",
        "order_accepted_enroute": "Ваш заказ #{order_id} принят! Водитель в пути.",
        "driver_arrived": "Водитель прибыл!",
        "order_completed_rate": (
            "Ваш заказ #{order_id} завершён!\nЦена: {price} сум\n"
            "Оцените водителя: отправьте число от 1 до 5."
        ),
        "referral_info": (
            "Ваша пригласительная ссылка:\n{link}\n\n"
            "Если друг присоединится по этой ссылке и завершит первый заказ, "
            "вам начислится {bonus} сум бонуса.\n\n"
            "Текущий бонусный баланс: {balance} сум"
        ),
    },
}


def t(key: str, lang: str | None, **kwargs) -> str:
    lang = lang if lang in TRANSLATIONS else "uz"
    template = TRANSLATIONS[lang].get(key) or TRANSLATIONS["uz"].get(key, key)
    return template.format(**kwargs) if kwargs else template
