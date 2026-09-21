from __future__ import annotations

import datetime
import re
import time

from aiogram import Bot
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select

import client_bot
from billing import apply_bonus_balance, apply_promo_discount
from config import DRIVER_BOT_TOKEN, SMS_PROVIDER, STORE_LAT, STORE_LON
from database import Driver, Order, PromoCode, Store, User, async_session, generate_referral_code, get_settings, init_db
from mobile_auth import OtpCooldownError, create_access_token, create_otp, get_current_user, verify_otp
from monitoring import init_sentry
from pricing import calculate_delivery_price, calculate_taxi_price
from routing import get_route_distance_km
from sms import send_sms

init_sentry()

app = FastAPI(title="Mobil ilova API")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


# ---------------------------------------------------------------------------
# Oddiy IP darajasidagi tezlik cheklovi (himoya qatlami sifatida qo'shimcha -
# asosiy himoya OTP cooldown/urinish limitida). Bitta jarayon xotirasida
# ishlaydi; bir nechta server nusxasi bo'lsa, Redis asosidagi yechimga o'ting.
# ---------------------------------------------------------------------------

_auth_request_log: dict[str, list[float]] = {}
_AUTH_RATE_LIMIT = 10  # bir IP uchun oyna ichida ruxsat etilgan so'rovlar
_AUTH_RATE_WINDOW_SECONDS = 60


def _check_ip_rate_limit(ip: str) -> None:
    now = time.time()
    timestamps = [t for t in _auth_request_log.get(ip, []) if now - t < _AUTH_RATE_WINDOW_SECONDS]
    if len(timestamps) >= _AUTH_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Juda ko'p so'rov. Biroz kuting.")
    timestamps.append(now)
    _auth_request_log[ip] = timestamps


PHONE_RE = re.compile(r"^\+?998\d{9}$")


def _validate_uzbek_phone(value: str) -> str:
    cleaned = value.strip().replace(" ", "")
    if not PHONE_RE.match(cleaned):
        raise ValueError("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak")
    return cleaned if cleaned.startswith("+") else f"+{cleaned}"


# ---------------------------------------------------------------------------
# Sxemalar
# ---------------------------------------------------------------------------


class RequestOtpBody(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v: str) -> str:
        return _validate_uzbek_phone(v)


class VerifyOtpBody(BaseModel):
    phone: str
    code: str
    full_name: str | None = None
    language: str = "uz"
    referral_code: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v: str) -> str:
        return _validate_uzbek_phone(v)

    @field_validator("code")
    @classmethod
    def _code_valid(cls, v: str) -> str:
        if not v.isdigit() or len(v) > 8:
            raise ValueError("Kod noto'g'ri formatda")
        return v


class UpdateMeBody(BaseModel):
    full_name: str | None = None
    language: str | None = None


class TaxiQuoteBody(BaseModel):
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    promo_code: str | None = None


class TaxiOrderBody(TaxiQuoteBody):
    pickup_text: str
    dropoff_text: str
    scheduled_for: datetime.datetime | None = None


class DeliveryQuoteBody(BaseModel):
    store_id: int
    dropoff_lat: float
    dropoff_lon: float
    promo_code: str | None = None


class DeliveryOrderBody(DeliveryQuoteBody):
    items_text: str
    dropoff_text: str
    scheduled_for: datetime.datetime | None = None


class PromoValidateBody(BaseModel):
    code: str


class RateOrderBody(BaseModel):
    rating: int


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------


async def _get_surge_multiplier() -> float:
    async with async_session() as session:
        settings = await get_settings(session)
        return settings.surge_multiplier


async def _apply_promo_and_bonus(
    base_price: float, promo_code: str | None, user: User
) -> tuple[float, float, str | None]:
    """Qaytaradi: (yakuniy_narx, umumiy_chegirma, ishlatilgan_promo_kod)."""
    discount = 0.0
    applied_code = None
    if promo_code:
        async with async_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == promo_code.upper(), PromoCode.is_active.is_(True))
            )
            promo = result.scalar_one_or_none()
            if promo and (promo.max_uses is None or promo.used_count < promo.max_uses):
                discount = apply_promo_discount(base_price, promo.discount_percent)
                promo.used_count += 1
                applied_code = promo.code
                await session.commit()

    price_after_promo = base_price - discount
    final_price, bonus_used = apply_bonus_balance(price_after_promo, user.bonus_balance)
    if bonus_used > 0:
        async with async_session() as session:
            db_user = await session.get(User, user.id)
            db_user.bonus_balance -= bonus_used
            await session.commit()
    return final_price, discount + bonus_used, applied_code


async def _dispatch(order_id: int, vehicle_type: str | None) -> None:
    bot = Bot(token=DRIVER_BOT_TOKEN)
    try:
        await client_bot.dispatch_order_to_driver(order_id, bot, vehicle_type=vehicle_type)
    finally:
        await bot.session.close()


def _order_to_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "order_type": o.order_type,
        "status": o.status,
        "pickup_location": o.pickup_location,
        "dropoff_location": o.dropoff_location,
        "distance_km": o.distance_km,
        "price": o.price,
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "driver_rating": o.driver_rating,
        "scheduled_for": o.scheduled_for.isoformat() if o.scheduled_for else None,
        "created_at": o.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Autentifikatsiya
# ---------------------------------------------------------------------------


@app.post("/api/v1/auth/request-otp")
async def request_otp(body: RequestOtpBody, request: Request):
    _check_ip_rate_limit(request.client.host if request.client else "unknown")
    try:
        code = await create_otp(body.phone)
    except OtpCooldownError as e:
        raise HTTPException(
            status_code=429, detail=f"Juda tez-tez so'ralmoqda. {e.retry_after_seconds} soniyadan keyin urining."
        )
    sent = await send_sms(body.phone, f"Tasdiqlash kodi: {code}")
    response = {"sent": sent}
    if SMS_PROVIDER != "eskiz":
        response["dev_code"] = code  # faqat SMS sozlanmagan (dev) holatda
    return response


@app.post("/api/v1/auth/verify-otp")
async def verify_otp_endpoint(body: VerifyOtpBody, request: Request):
    _check_ip_rate_limit(request.client.host if request.client else "unknown")
    if not await verify_otp(body.phone, body.code):
        raise HTTPException(status_code=400, detail="Kod noto'g'ri yoki muddati tugagan")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == body.phone))
        user = result.scalar_one_or_none()
        if not user:
            referrer = None
            if body.referral_code:
                ref_result = await session.execute(select(User).where(User.referral_code == body.referral_code))
                referrer = ref_result.scalar_one_or_none()
            code = await generate_referral_code(session)
            user = User(
                telegram_id=None,
                full_name=body.full_name or "Mijoz",
                phone=body.phone,
                language=body.language,
                referral_code=code,
                referred_by_id=referrer.id if referrer else None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    token = create_access_token(user.id)
    return {"token": token, "user_id": user.id, "full_name": user.full_name}


@app.get("/api/v1/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "phone": user.phone,
        "language": user.language,
        "bonus_balance": user.bonus_balance,
        "referral_code": user.referral_code,
    }


@app.put("/api/v1/me")
async def update_me(body: UpdateMeBody, user: User = Depends(get_current_user)):
    async with async_session() as session:
        db_user = await session.get(User, user.id)
        if body.full_name:
            db_user.full_name = body.full_name
        if body.language:
            db_user.language = body.language
        await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Do'konlar
# ---------------------------------------------------------------------------


@app.get("/api/v1/stores")
async def list_stores():
    async with async_session() as session:
        result = await session.execute(select(Store).where(Store.is_active.is_(True)))
        stores = result.scalars().all()
    return [{"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon} for s in stores]


# ---------------------------------------------------------------------------
# Taksi
# ---------------------------------------------------------------------------


@app.post("/api/v1/orders/taxi/quote")
async def taxi_quote(body: TaxiQuoteBody, user: User = Depends(get_current_user)):
    distance_km = await get_route_distance_km(body.pickup_lat, body.pickup_lon, body.dropoff_lat, body.dropoff_lon)
    base_price = calculate_taxi_price(distance_km, surge_multiplier=await _get_surge_multiplier())
    final_price, discount, applied_code = await _apply_promo_and_bonus(base_price, body.promo_code, user)
    return {
        "distance_km": round(distance_km, 1),
        "base_price": base_price,
        "discount": discount,
        "final_price": final_price,
        "promo_applied": applied_code,
    }


@app.post("/api/v1/orders/taxi")
async def create_taxi_order(body: TaxiOrderBody, user: User = Depends(get_current_user)):
    distance_km = await get_route_distance_km(body.pickup_lat, body.pickup_lon, body.dropoff_lat, body.dropoff_lon)
    base_price = calculate_taxi_price(distance_km, surge_multiplier=await _get_surge_multiplier())
    final_price, discount, applied_code = await _apply_promo_and_bonus(base_price, body.promo_code, user)

    async with async_session() as session:
        order = Order(
            user_id=user.id,
            order_type="taxi",
            pickup_location=body.pickup_text,
            dropoff_location=body.dropoff_text,
            pickup_lat=body.pickup_lat,
            pickup_lon=body.pickup_lon,
            dropoff_lat=body.dropoff_lat,
            dropoff_lon=body.dropoff_lon,
            distance_km=distance_km,
            price=final_price,
            promo_code=applied_code,
            discount_amount=discount,
            scheduled_for=body.scheduled_for,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

    if not body.scheduled_for:
        await _dispatch(order.id, vehicle_type="car")

    return _order_to_dict(order)


# ---------------------------------------------------------------------------
# Yetkazib berish
# ---------------------------------------------------------------------------


@app.post("/api/v1/orders/delivery/quote")
async def delivery_quote(body: DeliveryQuoteBody, user: User = Depends(get_current_user)):
    async with async_session() as session:
        store = await session.get(Store, body.store_id)
    store_lat, store_lon = (store.lat, store.lon) if store else (STORE_LAT, STORE_LON)
    distance_km = await get_route_distance_km(store_lat, store_lon, body.dropoff_lat, body.dropoff_lon)
    base_price = calculate_delivery_price(distance_km, surge_multiplier=await _get_surge_multiplier())
    final_price, discount, applied_code = await _apply_promo_and_bonus(base_price, body.promo_code, user)
    return {
        "distance_km": round(distance_km, 1),
        "base_price": base_price,
        "discount": discount,
        "final_price": final_price,
        "promo_applied": applied_code,
    }


@app.post("/api/v1/orders/delivery")
async def create_delivery_order(body: DeliveryOrderBody, user: User = Depends(get_current_user)):
    async with async_session() as session:
        store = await session.get(Store, body.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi")

    distance_km = await get_route_distance_km(store.lat, store.lon, body.dropoff_lat, body.dropoff_lon)
    base_price = calculate_delivery_price(distance_km, surge_multiplier=await _get_surge_multiplier())
    final_price, discount, applied_code = await _apply_promo_and_bonus(base_price, body.promo_code, user)

    async with async_session() as session:
        order = Order(
            user_id=user.id,
            order_type="delivery",
            pickup_location=store.name,
            dropoff_location=body.dropoff_text,
            pickup_lat=store.lat,
            pickup_lon=store.lon,
            dropoff_lat=body.dropoff_lat,
            dropoff_lon=body.dropoff_lon,
            store_id=store.id,
            distance_km=distance_km,
            items_text=body.items_text,
            price=final_price,
            promo_code=applied_code,
            discount_amount=discount,
            scheduled_for=body.scheduled_for,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

    if not body.scheduled_for:
        await _dispatch(order.id, vehicle_type=None)

    return _order_to_dict(order)


# ---------------------------------------------------------------------------
# Buyurtmalar: tarix, holat, bekor qilish, baholash
# ---------------------------------------------------------------------------


@app.get("/api/v1/orders")
async def list_orders(user: User = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(50)
        )
        orders = result.scalars().all()
    return [_order_to_dict(o) for o in orders]


@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: int, user: User = Depends(get_current_user)):
    async with async_session() as session:
        order = await session.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    return _order_to_dict(order)


@app.post("/api/v1/orders/{order_id}/cancel")
async def cancel_order(order_id: int, user: User = Depends(get_current_user)):
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.user_id != user.id or order.status not in ("pending", "offered"):
            raise HTTPException(status_code=400, detail="Bu buyurtmani bekor qilib bo'lmaydi")
        if order.driver_id:
            driver = await session.get(Driver, order.driver_id)
            if driver and driver.status == "busy":
                driver.status = "online"
        order.status = "cancelled"
        order.cancelled_by = "user"
        order.driver_id = None
        await session.commit()
    return {"ok": True}


@app.post("/api/v1/orders/{order_id}/rate")
async def rate_order(order_id: int, body: RateOrderBody, user: User = Depends(get_current_user)):
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="Baho 1 dan 5 gacha bo'lishi kerak")
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.user_id != user.id or order.status != "completed" or order.driver_rating is not None:
            raise HTTPException(status_code=400, detail="Bu buyurtmani baholab bo'lmaydi")
        order.driver_rating = body.rating
        driver = await session.get(Driver, order.driver_id) if order.driver_id else None
        if driver:
            total = driver.rating * driver.rating_count + body.rating
            driver.rating_count += 1
            driver.rating = total / driver.rating_count
        await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Promo va referal
# ---------------------------------------------------------------------------


@app.post("/api/v1/promo/validate")
async def validate_promo(body: PromoValidateBody):
    async with async_session() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == body.code.upper(), PromoCode.is_active.is_(True))
        )
        promo = result.scalar_one_or_none()
    if not promo or (promo.max_uses is not None and promo.used_count >= promo.max_uses):
        return {"valid": False}
    return {"valid": True, "discount_percent": promo.discount_percent}


@app.get("/api/v1/referral")
async def get_referral(user: User = Depends(get_current_user)):
    return {"referral_code": user.referral_code, "bonus_balance": user.bonus_balance}
