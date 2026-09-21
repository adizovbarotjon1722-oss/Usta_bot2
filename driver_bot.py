from __future__ import annotations

import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import select

from config import ADMIN_IDS, PLATFORM_COMMISSION_PERCENT, REFERRAL_BONUS_AMOUNT
from database import Driver, Order, PricingZone, SosAlert, User, async_session, get_settings
from pricing import calculate_open_route_price, haversine_km
from billing import calculate_commission
from translations import t

router = Router()


class DriverRegister(StatesGroup):
    name = State()
    phone = State()
    vehicle = State()
    license_photo = State()
    selfie_photo = State()


VEHICLE_MAP = {
    "🚗 Avtomobil": "car",
    "🏍 Mototsikl": "moto",
    "🚶 Piyoda (faqat yetkazib berish)": "foot",
}


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def vehicle_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Avtomobil"), KeyboardButton(text="🏍 Mototsikl")],
            [KeyboardButton(text="🚶 Piyoda (faqat yetkazib berish)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def online_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Onlayn"), KeyboardButton(text="⛔ Oflayn")],
            [KeyboardButton(text="🔥 Band hududlar")],
        ],
        resize_keyboard=True,
    )


async def get_driver(telegram_id: int) -> Driver | None:
    async with async_session() as session:
        result = await session.execute(select(Driver).where(Driver.telegram_id == telegram_id))
        return result.scalar_one_or_none()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    driver = await get_driver(message.from_user.id)
    if driver:
        if driver.is_blocked:
            await message.answer("Hisobingiz administrator tomonidan bloklangan. Bog'laning.")
        elif driver.is_approved:
            await message.answer(f"Xush kelibsiz, {driver.full_name}!", reply_markup=online_kb())
        else:
            await message.answer("Hujjatlaringiz hali tasdiqlanmagan. Iltimos, kuting.")
        return
    await message.answer(
        "Assalomu alaykum! Haydovchi/kuryer sifatida ro'yxatdan o'tamiz.\nIsmingizni kiriting:"
    )
    await state.set_state(DriverRegister.name)


@router.message(DriverRegister.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text)
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=phone_kb())
    await state.set_state(DriverRegister.phone)


@router.message(DriverRegister.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("Transport turini tanlang:", reply_markup=vehicle_kb())
    await state.set_state(DriverRegister.vehicle)


@router.message(DriverRegister.vehicle, F.text.in_(VEHICLE_MAP.keys()))
async def reg_vehicle(message: Message, state: FSMContext) -> None:
    await state.update_data(vehicle_type=VEHICLE_MAP[message.text])
    await message.answer(
        "Haydovchilik guvohnomangiz yoki shaxsingizni tasdiqlovchi hujjat rasmini yuboring:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(DriverRegister.license_photo)


@router.message(DriverRegister.license_photo, F.photo)
async def reg_license_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(license_photo_id=message.photo[-1].file_id)
    await message.answer(
        "Rahmat! Endi hujjatni qo'lingizda ushlab turgan holda yoki yuzingiz aniq ko'rinadigan "
        "selfi (o'zingiz) rasmingizni yuboring — bu haydovchi shaxsini tasdiqlash uchun kerak:"
    )
    await state.set_state(DriverRegister.selfie_photo)


@router.message(DriverRegister.selfie_photo, F.photo)
async def reg_selfie_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    selfie_photo_id = message.photo[-1].file_id
    async with async_session() as session:
        driver = Driver(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            vehicle_type=data["vehicle_type"],
            license_photo_id=data["license_photo_id"],
            selfie_photo_id=selfie_photo_id,
        )
        session.add(driver)
        await session.commit()
        await session.refresh(driver)
    await state.clear()
    await message.answer("Rahmat! Hujjatlaringiz admin tomonidan tekshirilmoqda.")
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_media_group(
                admin_id,
                media=[
                    InputMediaPhoto(
                        media=data["license_photo_id"],
                        caption=(
                            f"Yangi haydovchi #{driver.id}: {driver.full_name}, {driver.phone}, "
                            f"{driver.vehicle_type}\n1-rasm: hujjat, 2-rasm: selfi\n"
                            f"Tasdiqlash uchun: /approve {driver.id}"
                        ),
                    ),
                    InputMediaPhoto(media=selfie_photo_id),
                ],
            )
        except Exception:
            pass


@router.message(Command("approve"))
async def approve_driver(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /approve <driver_id>")
        return
    driver_id = int(parts[1])
    async with async_session() as session:
        driver = await session.get(Driver, driver_id)
        if not driver:
            await message.answer("Haydovchi topilmadi.")
            return
        driver.is_approved = True
        telegram_id = driver.telegram_id
        await session.commit()
    await message.bot.send_message(telegram_id, "Tabriklaymiz! Hujjatlaringiz tasdiqlandi. /start bosing.")
    await message.answer(f"Haydovchi #{driver_id} tasdiqlandi.")


@router.message(F.text == "🔥 Band hududlar")
async def zone_density(message: Message) -> None:
    driver = await get_driver(message.from_user.id)
    if not driver or not driver.is_approved or driver.is_blocked:
        return

    async with async_session() as session:
        settings = await get_settings(session)
        if settings.pricing_center_lat is None:
            await message.answer("Hududlar hali sozlanmagan (admin narx markazini belgilamagan).")
            return
        zone_result = await session.execute(
            select(PricingZone).where(PricingZone.is_active.is_(True)).order_by(PricingZone.min_km)
        )
        zones = zone_result.scalars().all()
        if not zones:
            await message.answer("Hududlar hali sozlanmagan (admin diapazon qo'shmagan).")
            return

        since = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        order_result = await session.execute(
            select(Order).where(
                Order.created_at >= since,
                Order.pickup_lat.is_not(None),
                Order.status.in_(["pending", "offered", "accepted", "in_progress", "completed"]),
            )
        )
        recent_orders = order_result.scalars().all()

    counts = {z.id: 0 for z in zones}
    for order in recent_orders:
        distance = haversine_km(settings.pricing_center_lat, settings.pricing_center_lon, order.pickup_lat, order.pickup_lon)
        for z in zones:
            if z.min_km <= distance < z.max_km:
                counts[z.id] += 1
                break

    lines = ["Oxirgi 3 soatdagi buyurtmalar hudud bo'yicha:"]
    for z in zones:
        lines.append(f"{z.min_km:g}-{z.max_km:g} km: {counts[z.id]} ta buyurtma")
    await message.answer("\n".join(lines))


@router.message(F.text == "✅ Onlayn")
async def go_online(message: Message) -> None:
    driver = await get_driver(message.from_user.id)
    if not driver or not driver.is_approved:
        await message.answer("Avval hujjatlaringiz tasdiqlanishi kerak.")
        return
    if driver.is_blocked:
        await message.answer("Hisobingiz administrator tomonidan bloklangan. Bog'laning.")
        return
    async with async_session() as session:
        db_driver = await session.get(Driver, driver.id)
        db_driver.status = "online"
        await session.commit()
    await message.answer("Siz onlaynsiz. Buyurtmalar kutilmoqda...", reply_markup=online_kb())


@router.message(F.text == "⛔ Oflayn")
async def go_offline(message: Message) -> None:
    driver = await get_driver(message.from_user.id)
    if not driver:
        return
    async with async_session() as session:
        db_driver = await session.get(Driver, driver.id)
        db_driver.status = "offline"
        await session.commit()
    await message.answer("Siz oflaynsiz.", reply_markup=online_kb())


@router.callback_query(F.data.startswith("accept:"))
async def accept_order(callback: CallbackQuery, client_bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])
    driver = await get_driver(callback.from_user.id)
    if not driver or not driver.is_approved or driver.is_blocked:
        await callback.answer("Sizda bu amalni bajarish huquqi yo'q.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.status != "offered" or order.driver_id != driver.id:
            await callback.answer("Bu buyurtma allaqachon band qilingan.", show_alert=True)
            return
        order.status = "accepted"
        db_driver = await session.get(Driver, driver.id)
        db_driver.status = "busy"
        user = await session.get(User, order.user_id)
        dropoff = order.dropoff_location
        user_telegram_id = user.telegram_id
        user_lang = user.language
        await session.commit()
    await callback.message.edit_text(
        f"Buyurtma #{order_id} qabul qilindi!\nManzil: {dropoff}\n\n"
        "Yetib borganda 'Yetib keldim' tugmasini bosing."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Yetib keldim", callback_data=f"arrived:{order_id}")],
            [InlineKeyboardButton(text="🆘 SOS", callback_data=f"sos:{order_id}")],
        ]
    )
    await callback.message.answer("Boshlash uchun:", reply_markup=kb)
    await callback.message.answer(
        "📍 Mijoz sizni xaritada kuzatib borishi uchun, xohlasangiz, jonli joylashuvingizni ulashing:\n"
        "📎 (qog'oz qisqich) → Joylashuv (Location) → Jonli joylashuvni yuborish (Share Live Location)."
    )
    client_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("sos_button", user_lang), callback_data=f"sos:{order_id}")]]
    )
    await client_bot.send_message(
        user_telegram_id,
        t("order_accepted_enroute", user_lang, order_id=order_id),
        reply_markup=client_kb,
    )


@router.callback_query(F.data.startswith("decline:"))
async def decline_order(callback: CallbackQuery) -> None:
    from client_bot import dispatch_order_to_driver

    order_id = int(callback.data.split(":")[1])
    driver = await get_driver(callback.from_user.id)
    if not driver:
        await callback.answer("Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.status != "offered" or order.driver_id != driver.id:
            await callback.answer("Bu buyurtma sizga tegishli emas yoki allaqachon hal qilingan.", show_alert=True)
            return
        order.status = "pending"
        order.driver_id = None
        vehicle_type = "car" if order.order_type in ("taxi", "taxi_open") else None
        await session.commit()
    await callback.message.edit_text(f"Buyurtma #{order_id} rad etildi.")
    await dispatch_order_to_driver(order_id, callback.bot, vehicle_type=vehicle_type)


@router.callback_query(F.data.startswith("arrived:"))
async def arrived(callback: CallbackQuery, client_bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])
    driver = await get_driver(callback.from_user.id)
    if not driver:
        await callback.answer("Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.driver_id != driver.id or order.status != "accepted":
            await callback.answer("Bu buyurtma sizga tegishli emas yoki holati mos emas.", show_alert=True)
            return
        order.status = "in_progress"
        order.trip_started_at = datetime.datetime.utcnow()
        user = await session.get(User, order.user_id)
        user_telegram_id = user.telegram_id
        user_lang = user.language
        await session.commit()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Bajarildi", callback_data=f"complete:{order_id}")],
            [InlineKeyboardButton(text="🆘 SOS", callback_data=f"sos:{order_id}")],
        ]
    )
    await callback.message.edit_text(f"Buyurtma #{order_id} — mijoz oldida. Yakunlash uchun tugmani bosing.")
    await callback.message.answer("Yakunlash:", reply_markup=kb)
    client_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("sos_button", user_lang), callback_data=f"sos:{order_id}")]]
    )
    await client_bot.send_message(user_telegram_id, t("driver_arrived", user_lang), reply_markup=client_kb)


@router.callback_query(F.data.startswith("sos:"))
async def driver_sos(callback: CallbackQuery, client_bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])
    driver = await get_driver(callback.from_user.id)
    if not driver:
        await callback.answer("Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.driver_id != driver.id:
            await callback.answer()
            return
        session.add(SosAlert(order_id=order_id, triggered_by="driver"))
        await session.commit()
        user = await session.get(User, order.user_id)

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🆘 SOS! Haydovchi tomonidan. Buyurtma #{order_id}\n"
                f"Haydovchi: {driver.full_name}, {driver.phone}\n"
                + (f"Mijoz: {user.full_name}, {user.phone}" if user else ""),
            )
        except Exception:
            pass
    if user:
        try:
            await client_bot.send_message(user.telegram_id, f"🆘 Haydovchi SOS tugmasini bosdi! Buyurtma #{order_id}")
        except Exception:
            pass

    await callback.answer("SOS signali yuborildi! Administrator xabardor qilindi.", show_alert=True)


@router.callback_query(F.data.startswith("complete:"))
async def complete_order(callback: CallbackQuery, client_bot: Bot, client_dp: Dispatcher) -> None:
    from client_bot import RateOrder

    order_id = int(callback.data.split(":")[1])
    calling_driver = await get_driver(callback.from_user.id)
    if not calling_driver:
        await callback.answer("Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.driver_id != calling_driver.id or order.status != "in_progress":
            await callback.answer("Bu buyurtma sizga tegishli emas yoki holati mos emas.", show_alert=True)
            return
        order.status = "completed"
        order.completed_at = datetime.datetime.utcnow()

        if order.order_type == "taxi_open" and order.trip_started_at:
            elapsed_minutes = (order.completed_at - order.trip_started_at).total_seconds() / 60
            settings = await get_settings(session)
            order.price = calculate_open_route_price(elapsed_minutes, settings.surge_multiplier)

        commission = calculate_commission(order.price, PLATFORM_COMMISSION_PERCENT)
        order.commission_amount = commission

        driver = await session.get(Driver, order.driver_id)
        driver.status = "online"
        driver.balance_owed += commission

        user = await session.get(User, order.user_id)
        price = order.price
        user_telegram_id = user.telegram_id
        user_lang = user.language
        tracking_message_id = order.driver_tracking_message_id

        # Agar bu foydalanuvchining birinchi yakunlangan buyurtmasi bo'lsa va u
        # kimningdir taklifi bilan qo'shilgan bo'lsa, taklif qilgan kishiga bonus.
        if user.referred_by_id:
            completed_count_result = await session.execute(
                select(Order).where(Order.user_id == user.id, Order.status == "completed")
            )
            completed_orders = completed_count_result.scalars().all()
            if len(completed_orders) == 1:  # aynan shu buyurtma - demak birinchisi
                referrer = await session.get(User, user.referred_by_id)
                if referrer:
                    referrer.bonus_balance += REFERRAL_BONUS_AMOUNT
                    try:
                        await client_bot.send_message(
                            referrer.telegram_id,
                            f"🎁 Do'stingiz birinchi buyurtmasini yakunladi! Sizga {REFERRAL_BONUS_AMOUNT:,.0f} so'm bonus qo'shildi.",
                        )
                    except Exception:
                        pass

        await session.commit()
    await callback.message.edit_text(f"Buyurtma #{order_id} yakunlandi. Rahmat!")

    if tracking_message_id:
        try:
            await client_bot.stop_message_live_location(chat_id=user_telegram_id, message_id=tracking_message_id)
        except Exception:
            pass

    key = StorageKey(bot_id=client_bot.id, chat_id=user_telegram_id, user_id=user_telegram_id)
    client_fsm = FSMContext(storage=client_dp.storage, key=key)
    await client_fsm.set_state(RateOrder.waiting)
    await client_fsm.update_data(order_id=order_id)

    await client_bot.send_message(
        user_telegram_id,
        t("order_completed_rate", user_lang, order_id=order_id, price=f"{price:,.0f}"),
    )


# ---------------------------------------------------------------------------
# Jonli joylashuv (mijoz haydovchini xaritada kuzatishi uchun)
# ---------------------------------------------------------------------------


async def _find_active_order_for_driver(driver_telegram_id: int) -> tuple[Order | None, User | None]:
    async with async_session() as session:
        driver = await get_driver(driver_telegram_id)
        if not driver:
            return None, None
        result = await session.execute(
            select(Order)
            .where(Order.driver_id == driver.id, Order.status.in_(["accepted", "in_progress"]))
            .order_by(Order.created_at.desc())
        )
        order = result.scalars().first()
        if not order:
            return None, None
        user = await session.get(User, order.user_id)
        return order, user


@router.message(F.location)
async def driver_shares_live_location(message: Message, client_bot: Bot) -> None:
    """Haydovchi jonli joylashuvni ulashishni boshlaganda ishga tushadi -
    buni mijozga ham jonli joylashuv sifatida yuboradi."""
    if message.location.live_period is None:
        return  # oddiy (bir martalik) joylashuv - bu yerda kerak emas

    order, user = await _find_active_order_for_driver(message.from_user.id)
    if not order or not user:
        return

    try:
        sent = await client_bot.send_location(
            user.telegram_id,
            latitude=message.location.latitude,
            longitude=message.location.longitude,
            live_period=message.location.live_period,
        )
    except Exception:
        return

    async with async_session() as session:
        db_order = await session.get(Order, order.id)
        if db_order:
            db_order.driver_tracking_message_id = sent.message_id
            await session.commit()


@router.edited_message(F.location)
async def driver_updates_live_location(message: Message, client_bot: Bot) -> None:
    """Haydovchi jonli joylashuvni yangilaganda (Telegram avtomatik yuboradi) -
    mijozga ko'rsatilayotgan xaritani ham shunga mos yangilaydi."""
    if message.location.live_period is None:
        return

    order, user = await _find_active_order_for_driver(message.from_user.id)
    if not order or not user or not order.driver_tracking_message_id:
        return

    try:
        await client_bot.edit_message_live_location(
            chat_id=user.telegram_id,
            message_id=order.driver_tracking_message_id,
            latitude=message.location.latitude,
            longitude=message.location.longitude,
        )
    except Exception:
        pass


@router.message(F.text)
async def fallback_text(message: Message) -> None:
    """Boshqa hech qanday handlerga to'g'ri kelmagan matn uchun - holatga mos
    aniq javob beradi, jim qolmaydi."""
    driver = await get_driver(message.from_user.id)
    if not driver:
        await message.answer("Ro'yxatdan o'tish uchun /start buyrug'ini yuboring.")
    elif driver.is_blocked:
        await message.answer("Hisobingiz administrator tomonidan bloklangan. Bog'laning.")
    elif not driver.is_approved:
        await message.answer("Hujjatlaringiz hali tasdiqlanmagan. Iltimos, kuting.")
    else:
        await message.answer("Quyidagi tugmalardan birini tanlang:", reply_markup=online_kb())
