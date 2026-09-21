from __future__ import annotations

import datetime

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import func, select

from config import (
    ADMIN_IDS,
    CANCEL_LIMIT,
    CANCEL_WINDOW_HOURS,
    CLICK_MERCHANT_ID,
    FIRST_ORDER_DISCOUNT_PERCENT,
    OPEN_ROUTE_BASE_FARE,
    OPEN_ROUTE_PRICE_PER_MINUTE,
    PAYME_MERCHANT_ID,
    REFERRAL_BONUS_AMOUNT,
    STORE_LAT,
    STORE_LON,
)
from database import Driver, Order, PricingZone, PromoCode, SosAlert, Store, User, async_session, generate_referral_code, get_settings
from matching import find_available_driver
from payments.click import generate_click_link
from payments.payme import generate_payme_link
from pricing import calculate_delivery_price, calculate_taxi_price, find_zone_price, haversine_km, is_daytime
from routing import get_route_distance_km
from translations import t
from billing import apply_bonus_balance, apply_promo_discount

router = Router()


class Register(StatesGroup):
    language = State()
    name = State()
    phone = State()


class TaxiOrder(StatesGroup):
    pickup = State()
    dropoff = State()
    when = State()
    schedule_time = State()
    confirm = State()


class OpenRouteOrder(StatesGroup):
    pickup = State()
    confirm = State()


class DeliveryOrder(StatesGroup):
    items = State()
    store = State()
    dropoff = State()
    when = State()
    schedule_time = State()
    confirm = State()


class RateOrder(StatesGroup):
    waiting = State()


TEXT_ADDRESS_BUTTON = "✍️ Manzilni yozish / Написать адрес"


def language_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_taxi", lang)), KeyboardButton(text=t("menu_open_route", lang))],
            [KeyboardButton(text=t("menu_delivery", lang))],
            [KeyboardButton(text=t("menu_orders", lang)), KeyboardButton(text=t("menu_referral", lang))],
        ],
        resize_keyboard=True,
    )


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("phone_button", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("loc_or_text", lang), request_location=True)],
            [KeyboardButton(text=TEXT_ADDRESS_BUTTON)],
        ],
        resize_keyboard=True,
    )


def when_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("when_now", lang)), KeyboardButton(text=t("when_later", lang))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def is_cancel_restricted(user_id: int) -> bool:
    """So'nggi CANCEL_WINDOW_HOURS ichida CANCEL_LIMIT martadan ko'p bekor qilgan
    mijozlar vaqtincha yangi buyurtma bera olmaydi - bu haydovchilarni behuda
    urinishlardan himoya qiladi."""
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=CANCEL_WINDOW_HOURS)
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.cancelled_by == "user",
                Order.created_at >= since,
            )
        )
        return len(result.scalars().all()) >= CANCEL_LIMIT


async def get_surge_multiplier() -> float:
    async with async_session() as session:
        settings = await get_settings(session)
        return settings.surge_multiplier


async def get_taxi_price(pickup_lat: float | None, pickup_lon: float | None, distance_km: float | None) -> float:
    """Avval admin belgilagan diapazon (zona) narxlashni tekshiradi - agar
    narx markazi va faol diapazonlar sozlangan bo'lsa, qayerdan olib
    ketilayotgan nuqtaning markazdan masofasiga va kunduzgi/kechgi vaqtga
    qarab qat'iy narx qo'llanadi. Sozlanmagan bo'lsa (yoki mos diapazon
    topilmasa) - oddiy masofa*narx formulasiga qaytadi. Ikkala holatda ham
    surge koeffitsienti ustiga qo'llanadi."""
    async with async_session() as session:
        settings = await get_settings(session)
        surge = settings.surge_multiplier
        if settings.pricing_center_lat is not None and pickup_lat is not None:
            result = await session.execute(select(PricingZone).where(PricingZone.is_active.is_(True)))
            zones = result.scalars().all()
            if zones:
                distance_from_center = haversine_km(
                    settings.pricing_center_lat, settings.pricing_center_lon, pickup_lat, pickup_lon
                )
                is_day = is_daytime(datetime.datetime.now().hour, settings.day_start_hour, settings.day_end_hour)
                zone_price = find_zone_price(distance_from_center, zones, is_day)
                if zone_price is not None:
                    return round(zone_price * surge, -2)
    return calculate_taxi_price(distance_km, surge_multiplier=surge)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject) -> None:
    user = await get_user(message.from_user.id)
    if user:
        if user.is_blocked:
            await message.answer(t("account_blocked", user.language))
            return
        await message.answer(
            t("welcome_back", user.language, name=user.full_name), reply_markup=main_menu_kb(user.language)
        )
        return
    await state.update_data(referral_payload=command.args)
    await message.answer(t("choose_language", "uz"), reply_markup=language_kb())
    await state.set_state(Register.language)


@router.message(Register.language)
async def reg_language(message: Message, state: FSMContext) -> None:
    lang = "ru" if "рус" in (message.text or "").lower() else "uz"
    await state.update_data(language=lang)
    await message.answer(t("ask_name", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(Register.name)


@router.message(Register.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(full_name=message.text)
    await message.answer(t("ask_phone", lang), reply_markup=phone_kb(lang))
    await state.set_state(Register.phone)


@router.message(Register.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    referral_payload = data.get("referral_payload")

    async with async_session() as session:
        referrer = None
        if referral_payload:
            result = await session.execute(select(User).where(User.referral_code == referral_payload))
            referrer = result.scalar_one_or_none()

        phone = message.contact.phone_number
        existing_result = await session.execute(select(User).where(User.phone == phone))
        existing_user = existing_result.scalar_one_or_none()
        if existing_user:
            # Bu telefon raqami bilan mobil ilova orqali oldin ro'yxatdan o'tgan -
            # endi shu hisobni Telegram akkauntiga bog'laymiz, ikki marta yaratmaymiz.
            existing_user.telegram_id = message.from_user.id
            await session.commit()
        else:
            code = await generate_referral_code(session)
            user = User(
                telegram_id=message.from_user.id,
                full_name=data["full_name"],
                phone=phone,
                language=lang,
                referral_code=code,
                referred_by_id=referrer.id if referrer else None,
            )
            session.add(user)
            await session.commit()

    await state.clear()
    if referrer:
        await message.answer(t("referral_applied", lang, name=referrer.full_name))
    await message.answer(t("registered", lang), reply_markup=main_menu_kb(lang))


@router.message(Register.phone)
async def reg_phone_invalid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "uz")
    await message.answer(t("invalid_phone", lang), reply_markup=phone_kb(lang))


# ---------------------------------------------------------------------------
# Referal
# ---------------------------------------------------------------------------


@router.message(F.text.in_([t("menu_referral", "uz"), t("menu_referral", "ru")]))
async def referral_info(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        return
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user.referral_code}"
    await message.answer(
        t(
            "referral_info",
            user.language,
            link=link,
            bonus=f"{REFERRAL_BONUS_AMOUNT:,.0f}",
            balance=f"{user.bonus_balance:,.0f}",
        )
    )


# ---------------------------------------------------------------------------
# Taksi
# ---------------------------------------------------------------------------


@router.message(F.text.in_([t("menu_taxi", "uz"), t("menu_taxi", "ru")]))
async def taxi_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    if user and user.is_blocked:
        await message.answer(t("account_blocked", lang))
        return
    if user and await is_cancel_restricted(user.id):
        await message.answer(t("cancel_restricted", lang, hours=CANCEL_WINDOW_HOURS))
        return
    await message.answer(t("ask_pickup", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(TaxiOrder.pickup)


@router.message(TaxiOrder.pickup, F.location)
async def taxi_pickup_location(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(
        pickup_text="Joylashuv (GPS)", pickup_lat=message.location.latitude, pickup_lon=message.location.longitude
    )
    await message.answer(t("ask_dropoff", lang), reply_markup=location_kb(lang))
    await state.set_state(TaxiOrder.dropoff)


@router.message(TaxiOrder.pickup)
async def taxi_pickup_text(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(pickup_text=message.text, pickup_lat=None, pickup_lon=None)
    await message.answer(t("ask_dropoff", lang), reply_markup=location_kb(lang))
    await state.set_state(TaxiOrder.dropoff)


@router.message(TaxiOrder.dropoff, F.location)
async def taxi_dropoff_location(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(
        dropoff_text="Joylashuv (GPS)", dropoff_lat=message.location.latitude, dropoff_lon=message.location.longitude
    )
    await ask_when(message, state, lang, is_taxi=True)


@router.message(TaxiOrder.dropoff, F.text == TEXT_ADDRESS_BUTTON)
async def taxi_dropoff_ask_text(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(t("type_address_prompt", lang), reply_markup=ReplyKeyboardRemove())
    await state.update_data(_awaiting="dropoff_text_taxi")


@router.message(TaxiOrder.dropoff)
async def taxi_dropoff_text(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(dropoff_text=message.text, dropoff_lat=None, dropoff_lon=None, _awaiting=None)
    await ask_when(message, state, lang, is_taxi=True)


async def ask_when(message: Message, state: FSMContext, lang: str, is_taxi: bool) -> None:
    await message.answer(t("ask_when", lang), reply_markup=when_kb(lang))
    await state.set_state(TaxiOrder.when if is_taxi else DeliveryOrder.when)


@router.message(TaxiOrder.when, F.text.in_([t("when_now", "uz"), t("when_now", "ru")]))
async def taxi_when_now(message: Message, state: FSMContext) -> None:
    await state.update_data(scheduled_for=None)
    await show_taxi_confirmation(message, state)


@router.message(TaxiOrder.when, F.text.in_([t("when_later", "uz"), t("when_later", "ru")]))
async def taxi_when_later(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(t("ask_schedule_time", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(TaxiOrder.schedule_time)


@router.message(TaxiOrder.schedule_time)
async def taxi_schedule_time(message: Message, state: FSMContext) -> None:
    await _handle_schedule_time(message, state, is_taxi=True)


async def _handle_schedule_time(message: Message, state: FSMContext, is_taxi: bool) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    try:
        when = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(t("schedule_invalid", lang))
        return
    if when <= datetime.datetime.now():
        await message.answer(t("schedule_past", lang))
        return

    await state.update_data(scheduled_for=when.isoformat())
    if is_taxi:
        await show_taxi_confirmation(message, state)
    else:
        await show_delivery_confirmation(message, state)


async def show_taxi_confirmation(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()

    distance_km = None
    if data.get("pickup_lat") is not None and data.get("dropoff_lat") is not None:
        distance_km = await get_route_distance_km(
            data["pickup_lat"], data["pickup_lon"], data["dropoff_lat"], data["dropoff_lon"]
        )
    price = await get_taxi_price(data.get("pickup_lat"), data.get("pickup_lon"), distance_km)
    await state.update_data(distance_km=distance_km, base_price=price, promo_code=None, discount=0.0)
    distance_line = f"Masofa: taxminan {distance_km:.1f} km\n" if distance_km is not None else ""
    await message.answer(
        t(
            "taxi_confirm",
            lang,
            pickup=data["pickup_text"],
            dropoff=data["dropoff_text"],
            distance_line=distance_line,
            price=f"{price:,.0f}",
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(TaxiOrder.confirm)


@router.message(TaxiOrder.confirm, F.text.lower().in_(["ha", "да"]))
async def taxi_confirm(message: Message, state: FSMContext, driver_bot: Bot) -> None:
    await finalize_order(message, state, driver_bot, order_type="taxi")


@router.message(TaxiOrder.confirm, F.text.lower().in_(["yo'q", "yoq", "нет"]))
async def taxi_cancel(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.clear()
    await message.answer(t("order_cancelled", lang), reply_markup=main_menu_kb(lang))


@router.message(TaxiOrder.confirm)
async def taxi_try_promo(message: Message, state: FSMContext) -> None:
    await try_apply_promo(message, state)


# ---------------------------------------------------------------------------
# Ochiq marshrut (mijoz o'zi yo'l ko'rsatib boradi, narx vaqt bo'yicha)
# ---------------------------------------------------------------------------


@router.message(F.text.in_([t("menu_open_route", "uz"), t("menu_open_route", "ru")]))
async def open_route_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    if user and user.is_blocked:
        await message.answer(t("account_blocked", lang))
        return
    if user and await is_cancel_restricted(user.id):
        await message.answer(t("cancel_restricted", lang, hours=CANCEL_WINDOW_HOURS))
        return
    await message.answer(t("open_route_intro", lang))
    await message.answer(t("open_route_ask_pickup", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(OpenRouteOrder.pickup)


@router.message(OpenRouteOrder.pickup, F.location)
async def open_route_pickup_location(message: Message, state: FSMContext) -> None:
    await state.update_data(
        pickup_text="Joylashuv (GPS)", pickup_lat=message.location.latitude, pickup_lon=message.location.longitude
    )
    await show_open_route_confirmation(message, state)


@router.message(OpenRouteOrder.pickup)
async def open_route_pickup_text(message: Message, state: FSMContext) -> None:
    await state.update_data(pickup_text=message.text, pickup_lat=None, pickup_lon=None)
    await show_open_route_confirmation(message, state)


async def show_open_route_confirmation(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()
    surge = await get_surge_multiplier()
    base_price = round(OPEN_ROUTE_BASE_FARE * surge, -2)
    await state.update_data(open_route_base_price=base_price)
    await message.answer(
        t(
            "open_route_confirm",
            lang,
            pickup=data["pickup_text"],
            base_price=f"{base_price:,.0f}",
            per_minute=f"{OPEN_ROUTE_PRICE_PER_MINUTE * surge:,.0f}",
        )
    )
    await state.set_state(OpenRouteOrder.confirm)


@router.message(OpenRouteOrder.confirm, F.text.lower().in_(["ha", "да"]))
async def open_route_confirm(message: Message, state: FSMContext, driver_bot: Bot) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()
    async with async_session() as session:
        order = Order(
            user_id=user.id,
            order_type="taxi_open",
            pickup_location=data["pickup_text"],
            dropoff_location="Yo'lda mijoz ko'rsatadi",
            pickup_lat=data.get("pickup_lat"),
            pickup_lon=data.get("pickup_lon"),
            price=data["open_route_base_price"],
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
    await state.clear()
    await message.answer(t("open_route_created", lang), reply_markup=main_menu_kb(lang))
    await dispatch_order_to_driver(order.id, driver_bot, vehicle_type="car")


@router.message(OpenRouteOrder.confirm, F.text.lower().in_(["yo'q", "yoq", "нет"]))
async def open_route_cancel(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.clear()
    await message.answer(t("order_cancelled", lang), reply_markup=main_menu_kb(lang))


# ---------------------------------------------------------------------------
# Yetkazib berish
# ---------------------------------------------------------------------------


@router.message(F.text.in_([t("menu_delivery", "uz"), t("menu_delivery", "ru")]))
async def delivery_start(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    if user and user.is_blocked:
        await message.answer(t("account_blocked", lang))
        return
    if user and await is_cancel_restricted(user.id):
        await message.answer(t("cancel_restricted", lang, hours=CANCEL_WINDOW_HOURS))
        return
    await message.answer(t("ask_items", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DeliveryOrder.items)


@router.message(DeliveryOrder.items)
async def delivery_items(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(items=message.text)

    async with async_session() as session:
        result = await session.execute(select(Store).where(Store.is_active.is_(True)))
        stores = result.scalars().all()

    if len(stores) <= 1:
        store = stores[0] if stores else None
        await state.update_data(
            store_id=store.id if store else None,
            store_lat=store.lat if store else STORE_LAT,
            store_lon=store.lon if store else STORE_LON,
            store_name=store.name if store else "Do'kon",
        )
        await message.answer(t("ask_delivery_address", lang), reply_markup=location_kb(lang))
        await state.set_state(DeliveryOrder.dropoff)
        return

    await state.update_data(_stores={s.name: (s.id, s.lat, s.lon) for s in stores})
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s.name)] for s in stores],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(t("choose_store", lang), reply_markup=kb)
    await state.set_state(DeliveryOrder.store)


@router.message(DeliveryOrder.store)
async def delivery_store_chosen(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()
    choice = data.get("_stores", {}).get(message.text)
    if not choice:
        await message.answer(t("choose_store", lang))
        return
    store_id, store_lat, store_lon = choice
    await state.update_data(store_id=store_id, store_lat=store_lat, store_lon=store_lon, store_name=message.text)
    await message.answer(t("ask_delivery_address", lang), reply_markup=location_kb(lang))
    await state.set_state(DeliveryOrder.dropoff)


@router.message(DeliveryOrder.dropoff, F.location)
async def delivery_dropoff_location(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(
        dropoff_text="Joylashuv (GPS)", dropoff_lat=message.location.latitude, dropoff_lon=message.location.longitude
    )
    await ask_when(message, state, lang, is_taxi=False)


@router.message(DeliveryOrder.dropoff, F.text == TEXT_ADDRESS_BUTTON)
async def delivery_dropoff_ask_text(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(t("type_address_prompt", lang), reply_markup=ReplyKeyboardRemove())
    await state.update_data(_awaiting="dropoff_text_delivery")


@router.message(DeliveryOrder.dropoff)
async def delivery_dropoff_text(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.update_data(dropoff_text=message.text, dropoff_lat=None, dropoff_lon=None, _awaiting=None)
    await ask_when(message, state, lang, is_taxi=False)


@router.message(DeliveryOrder.when, F.text.in_([t("when_now", "uz"), t("when_now", "ru")]))
async def delivery_when_now(message: Message, state: FSMContext) -> None:
    await state.update_data(scheduled_for=None)
    await show_delivery_confirmation(message, state)


@router.message(DeliveryOrder.when, F.text.in_([t("when_later", "uz"), t("when_later", "ru")]))
async def delivery_when_later(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(t("ask_schedule_time", lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(DeliveryOrder.schedule_time)


@router.message(DeliveryOrder.schedule_time)
async def delivery_schedule_time(message: Message, state: FSMContext) -> None:
    await _handle_schedule_time(message, state, is_taxi=False)


async def show_delivery_confirmation(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()

    distance_km = None
    store_lat = data.get("store_lat", STORE_LAT)
    store_lon = data.get("store_lon", STORE_LON)
    if data.get("dropoff_lat") is not None:
        distance_km = await get_route_distance_km(store_lat, store_lon, data["dropoff_lat"], data["dropoff_lon"])
    price = calculate_delivery_price(distance_km, surge_multiplier=await get_surge_multiplier())
    await state.update_data(distance_km=distance_km, base_price=price, promo_code=None, discount=0.0)
    distance_line = f"Masofa: taxminan {distance_km:.1f} km\n" if distance_km is not None else ""
    await message.answer(
        t(
            "delivery_confirm",
            lang,
            items=data["items"],
            dropoff=data["dropoff_text"],
            distance_line=distance_line,
            price=f"{price:,.0f}",
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(DeliveryOrder.confirm)


@router.message(DeliveryOrder.confirm, F.text.lower().in_(["ha", "да"]))
async def delivery_confirm(message: Message, state: FSMContext, driver_bot: Bot) -> None:
    await finalize_order(message, state, driver_bot, order_type="delivery")


@router.message(DeliveryOrder.confirm, F.text.lower().in_(["yo'q", "yoq", "нет"]))
async def delivery_cancel(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await state.clear()
    await message.answer(t("order_cancelled", lang), reply_markup=main_menu_kb(lang))


@router.message(DeliveryOrder.confirm)
async def delivery_try_promo(message: Message, state: FSMContext) -> None:
    await try_apply_promo(message, state)


# ---------------------------------------------------------------------------
# Promo-kod
# ---------------------------------------------------------------------------


async def try_apply_promo(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    code = (message.text or "").strip().upper()

    async with async_session() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code, PromoCode.is_active.is_(True))
        )
        promo = result.scalar_one_or_none()

    valid = promo and (promo.max_uses is None or promo.used_count < promo.max_uses)
    if not valid:
        await message.answer(t("promo_invalid", lang))
        return

    data = await state.get_data()
    base_price = data["base_price"]
    discount = apply_promo_discount(base_price, promo.discount_percent)
    new_price = max(base_price - discount, 0)
    await state.update_data(promo_code=code, discount=discount)
    await message.answer(t("promo_applied", lang, price=f"{new_price:,.0f}"))


# ---------------------------------------------------------------------------
# Buyurtmani yakunlash (umumiy, taksi va delivery uchun)
# ---------------------------------------------------------------------------


async def finalize_order(message: Message, state: FSMContext, driver_bot: Bot, order_type: str) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    data = await state.get_data()

    base_price = data["base_price"]
    discount = data.get("discount", 0.0)
    first_order_discount_applied = False
    if user and discount == 0 and FIRST_ORDER_DISCOUNT_PERCENT > 0:
        async with async_session() as check_session:
            count_result = await check_session.execute(
                select(func.count(Order.id)).where(Order.user_id == user.id, Order.status != "cancelled")
            )
            if count_result.scalar_one() == 0:
                discount = apply_promo_discount(base_price, FIRST_ORDER_DISCOUNT_PERCENT)
                first_order_discount_applied = True
    price_after_promo = max(base_price - discount, 0)

    final_price, bonus_used = apply_bonus_balance(price_after_promo, user.bonus_balance if user else 0.0)

    scheduled_for_raw = data.get("scheduled_for")
    scheduled_for = datetime.datetime.fromisoformat(scheduled_for_raw) if scheduled_for_raw else None

    async with async_session() as session:
        if order_type == "taxi":
            order = Order(
                user_id=user.id,
                order_type="taxi",
                pickup_location=data["pickup_text"],
                dropoff_location=data["dropoff_text"],
                pickup_lat=data.get("pickup_lat"),
                pickup_lon=data.get("pickup_lon"),
                dropoff_lat=data.get("dropoff_lat"),
                dropoff_lon=data.get("dropoff_lon"),
                distance_km=data.get("distance_km"),
                price=final_price,
                promo_code=data.get("promo_code"),
                discount_amount=discount + bonus_used,
                scheduled_for=scheduled_for,
            )
        else:
            order = Order(
                user_id=user.id,
                order_type="delivery",
                pickup_location=data.get("store_name", "Do'kon / jo'natuvchi"),
                dropoff_location=data["dropoff_text"],
                pickup_lat=data.get("store_lat", STORE_LAT),
                pickup_lon=data.get("store_lon", STORE_LON),
                store_id=data.get("store_id"),
                dropoff_lat=data.get("dropoff_lat"),
                dropoff_lon=data.get("dropoff_lon"),
                distance_km=data.get("distance_km"),
                items_text=data["items"],
                price=final_price,
                promo_code=data.get("promo_code"),
                discount_amount=discount + bonus_used,
                scheduled_for=scheduled_for,
            )
        session.add(order)

        if bonus_used > 0:
            db_user = await session.get(User, user.id)
            db_user.bonus_balance -= bonus_used

        promo_code = data.get("promo_code")
        if promo_code:
            promo_result = await session.execute(select(PromoCode).where(PromoCode.code == promo_code))
            promo = promo_result.scalar_one_or_none()
            if promo:
                promo.used_count += 1

        await session.commit()
        await session.refresh(order)

    await state.clear()

    if scheduled_for:
        await message.answer(
            t("scheduled_confirmed", lang, when=scheduled_for.strftime("%d.%m.%Y %H:%M")),
            reply_markup=main_menu_kb(lang),
        )
        return  # rejalashtirilgan buyurtma darhol dispetcherlanmaydi - background vazifa yuboradi

    key = "order_created_taxi" if order_type == "taxi" else "order_created_delivery"
    await message.answer(t(key, lang), reply_markup=main_menu_kb(lang))
    if first_order_discount_applied:
        await message.answer(t("first_order_discount_applied", lang, percent=int(FIRST_ORDER_DISCOUNT_PERCENT)))
    await dispatch_order_to_driver(order.id, driver_bot, vehicle_type="car" if order_type == "taxi" else None)
    await send_payment_options(message, order, lang)


async def send_payment_options(message: Message, order: Order, lang: str) -> None:
    buttons = []
    if PAYME_MERCHANT_ID:
        buttons.append(
            [InlineKeyboardButton(text=t("pay_payme", lang), url=generate_payme_link(order.id, order.price))]
        )
    if CLICK_MERCHANT_ID:
        buttons.append(
            [InlineKeyboardButton(text=t("pay_click", lang), url=generate_click_link(order.id, order.price))]
        )
    if not buttons:
        return
    await message.answer(t("pay_prompt", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


async def dispatch_order_to_driver(order_id: int, driver_bot: Bot, vehicle_type: str | None) -> None:
    """Mos haydovchini topib, unga buyurtmani taklif qiladi.
    Rad etilsa driver_bot.py shu funksiyani qayta chaqiradi (keyingi haydovchiga)."""
    driver = await find_available_driver(vehicle_type)
    if not driver:
        return
    async with async_session() as session:
        order = await session.get(Order, order_id)
        order.driver_id = driver.id
        order.status = "offered"
        await session.commit()
        type_labels = {"taxi": "🚗 Taksi", "taxi_open": "🧭 Ochiq marshrut", "delivery": "📦 Yetkazib berish"}
        type_label = type_labels.get(order.order_type, order.order_type)
        details = (
            f"{type_label}\n"
            f"Qayerdan: {order.pickup_location}\nQayerga: {order.dropoff_location}\n"
        )
        if order.order_type == "taxi_open":
            details += f"Boshlang'ich narx: {order.price:,.0f} so'm (safar davomida oshadi)"
        else:
            details += f"Narx: {order.price:,.0f} so'm"
        if order.distance_km:
            details += f"\nMasofa: taxminan {order.distance_km:.1f} km"
        details += f"\nTo'lov: {'onlayn' if order.payment_method != 'naqd' else 'naqd'}"
        if order.items_text:
            details += f"\nMahsulot: {order.items_text}"
        nav_lat, nav_lon = order.pickup_lat, order.pickup_lon
    buttons = [
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept:{order_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"decline:{order_id}"),
        ]
    ]
    if nav_lat and nav_lon:
        buttons.append(
            [InlineKeyboardButton(text="🗺 Xaritada ko'rish", url=f"https://maps.google.com/?q={nav_lat},{nav_lon}")]
        )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await driver_bot.send_message(driver.telegram_id, f"Yangi buyurtma #{order_id}\n{details}", reply_markup=kb)


# ---------------------------------------------------------------------------
# Buyurtmalar tarixi
# ---------------------------------------------------------------------------


@router.message(F.text.in_([t("menu_orders", "uz"), t("menu_orders", "ru")]))
async def my_orders(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    lang = user.language
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5)
        )
        orders = result.scalars().all()
    if not orders:
        await message.answer(t("no_orders", lang))
        return
    lines = [f"#{o.id} — {o.order_type} — {o.status} — {o.price:,.0f} so'm" for o in orders]
    buttons = [
        [InlineKeyboardButton(text=t("cancel_own_button", lang, order_id=o.id), callback_data=f"cancel_own:{o.id}")]
        for o in orders
        if o.status in ("pending", "offered")
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data.startswith("cancel_own:"))
async def cancel_own_order(callback: CallbackQuery, driver_bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        user = await get_user(callback.from_user.id)
        if not order or not user or order.user_id != user.id or order.status not in ("pending", "offered"):
            await callback.answer()
            return
        notify_driver_telegram_id = None
        if order.driver_id:
            db_driver = await session.get(Driver, order.driver_id)
            if db_driver:
                notify_driver_telegram_id = db_driver.telegram_id
                if db_driver.status == "busy":
                    db_driver.status = "online"
        order.status = "cancelled"
        order.cancelled_by = "user"
        order.driver_id = None
        await session.commit()
        lang = user.language

    if notify_driver_telegram_id:
        try:
            await driver_bot.send_message(
                notify_driver_telegram_id, f"Buyurtma #{order_id} mijoz tomonidan bekor qilindi."
            )
        except Exception:
            pass

    await callback.message.edit_text(t("order_cancelled_by_user", lang, order_id=order_id))
    await callback.answer()


# ---------------------------------------------------------------------------
# Reyting
# ---------------------------------------------------------------------------


@router.message(RateOrder.waiting)
async def rate_order(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 5):
        await message.answer(t("rate_prompt", lang))
        return
    rating_value = int(text)
    data = await state.get_data()
    order_id = data.get("order_id")
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order and order.driver_id and order.driver_rating is None:
            order.driver_rating = rating_value
            driver = await session.get(Driver, order.driver_id)
            total = driver.rating * driver.rating_count + rating_value
            driver.rating_count += 1
            driver.rating = total / driver.rating_count
            await session.commit()
    await state.clear()
    await message.answer(t("rate_thanks", lang), reply_markup=main_menu_kb(lang))


# ---------------------------------------------------------------------------
# SOS
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("sos:"))
async def client_sos(callback: CallbackQuery, driver_bot: Bot) -> None:
    order_id = int(callback.data.split(":")[1])
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    lang = user.language

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.user_id != user.id:
            await callback.answer()
            return
        session.add(SosAlert(order_id=order_id, triggered_by="client"))
        await session.commit()
        driver = await session.get(Driver, order.driver_id) if order.driver_id else None

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🆘 SOS! Mijoz tomonidan. Buyurtma #{order_id}\n"
                f"Mijoz: {user.full_name}, {user.phone}\n"
                + (f"Haydovchi: {driver.full_name}, {driver.phone}" if driver else ""),
            )
        except Exception:
            pass
    if driver:
        try:
            await driver_bot.send_message(driver.telegram_id, f"🆘 Mijoz SOS tugmasini bosdi! Buyurtma #{order_id}")
        except Exception:
            pass

    await callback.answer(t("sos_sent", lang), show_alert=True)
