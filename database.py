from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import DATABASE_URL, STORE_LAT, STORE_LON


class Base(DeclarativeBase):
    pass


class User(Base):
    """Mijoz - Telegram bot orqali (telegram_id bilan) yoki mobil ilova orqali
    (faqat phone bilan, telegram_id=None) ro'yxatdan o'tishi mumkin. Ikkalasi
    ham bitta jadvalda - shu tufayli buyurtmalar, bonus, referal bitta
    "hisob" atrofida birlashadi."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(2), default="uz")  # uz yoki ru
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    bonus_balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_blocked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Driver(Base):
    """Haydovchi yoki kuryer."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(32))
    vehicle_type: Mapped[str] = mapped_column(String(32))  # car, moto, foot
    status: Mapped[str] = mapped_column(String(16), default="offline")  # offline, online, busy
    is_approved: Mapped[bool] = mapped_column(default=False)
    is_blocked: Mapped[bool] = mapped_column(default=False)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    balance_owed: Mapped[float] = mapped_column(Float, default=0.0)  # platformaga to'lanishi kerak bo'lgan komissiya
    license_photo_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    selfie_photo_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="driver")


class Order(Base):
    """Buyurtma - taksi yoki yetkazib berish."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    order_type: Mapped[str] = mapped_column(String(16))  # taxi, taxi_open, delivery
    # pending -> offered -> accepted -> in_progress -> completed / cancelled
    status: Mapped[str] = mapped_column(String(24), default="pending")
    pickup_location: Mapped[str] = mapped_column(Text)
    dropoff_location: Mapped[str] = mapped_column(Text)
    pickup_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    dropoff_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    dropoff_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    items_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    commission_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    promo_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    scheduled_for: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(16), nullable=True)  # user, admin
    driver_tracking_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(16), default="naqd")  # naqd, onlayn
    payment_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # None (naqd), kutilmoqda, tolandi, bekor
    driver_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    trip_started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")
    driver: Mapped["Driver | None"] = relationship(back_populates="orders")


class Payment(Base):
    """Payme yoki Click orqali qilingan onlayn to'lov tranzaksiyasi."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    provider: Mapped[str] = mapped_column(String(16))  # payme, click
    provider_transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(16), default="created")  # created, performed, cancelled
    cancel_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    performed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class PromoCode(Base):
    """Chegirma promo-kodlari."""

    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    discount_percent: Mapped[int] = mapped_column(Integer)  # 1-100
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = cheksiz
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class SosAlert(Base):
    """Yo'l davomida bosilgan SOS tugmasi haqida yozuv (audit uchun)."""

    __tablename__ = "sos_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    triggered_by: Mapped[str] = mapped_column(String(16))  # client, driver
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class Store(Base):
    """Yetkazib berish uchun boshlang'ich nuqta (do'kon, ombor yoki hudud markazi).
    Bir nechta hudud/tumanda ishga tushirilsa, har biriga alohida yozuv qo'shiladi."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class OtpCode(Base):
    """Mobil ilova uchun telefon orqali kirish kodlari (bir martalik, muddati cheklangan)."""

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(8))
    is_used: Mapped[bool] = mapped_column(default=False)
    attempts: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class PlatformSettings(Base):
    """Yagona qatorli (id=1) global sozlamalar - surge koeffitsienti, narx
    markazi va kunduzgi/kechgi vaqt oralig'i."""

    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    surge_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    pricing_center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    pricing_center_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    day_start_hour: Mapped[int] = mapped_column(Integer, default=7)
    day_end_hour: Mapped[int] = mapped_column(Integer, default=22)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class PricingZone(Base):
    """Narx markazidan masofa bo'yicha diapazon (masalan 0-5km, 5-10km) -
    har biri uchun kunduzgi va kechgi qat'iy narx belgilanadi."""

    __tablename__ = "pricing_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    min_km: Mapped[float] = mapped_column(Float)
    max_km: Mapped[float] = mapped_column(Float)
    day_price: Mapped[float] = mapped_column(Float)
    night_price: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


async def get_settings(session) -> "PlatformSettings":
    """Global sozlamalar qatorini qaytaradi, mavjud bo'lmasa yaratadi."""
    settings = await session.get(PlatformSettings, 1)
    if settings is None:
        settings = PlatformSettings(id=1, surge_multiplier=1.0)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def generate_referral_code(session) -> str:
    """Takrorlanmas qisqa referal kod yaratadi (Telegram bot va mobil ilova
    API'si bir xil funksiyadan foydalanadi)."""
    import secrets

    while True:
        code = secrets.token_hex(3).upper()
        exists = await session.execute(select(User).where(User.referral_code == code))
        if not exists.scalar_one_or_none():
            return code


engine = create_async_engine(DATABASE_URL, echo=False)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Birinchi ishga tushirishda: sozlamalar qatori va kamida bitta do'kon nuqtasi borligini ta'minlaydi.
    async with async_session() as session:
        await get_settings(session)
        result = await session.execute(select(Store))
        if result.first() is None:
            session.add(Store(name="Asosiy nuqta", lat=STORE_LAT, lon=STORE_LON, is_active=True))
            await session.commit()
