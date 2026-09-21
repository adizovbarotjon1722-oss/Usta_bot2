from __future__ import annotations

import datetime

from sqlalchemy import select

from config import DAY_START_HOUR, NIGHT_START_HOUR, STORE_LAT, STORE_LON
from database import DistanceBand, Order, PricingCenter, async_session
from pricing import haversine_km


def is_night(when: datetime.datetime | None = None) -> bool:
    """Berilgan vaqt (yoki hozirgi vaqt) kechgi tarifga to'g'ri kelsa True.

    Standart: 22:00 dan 06:00 gacha kechgi tarif. Agar NIGHT_START_HOUR
    DAY_START_HOUR dan katta bo'lsa (masalan 22 > 6), kecha kun bo'yicha
    "aylanib o'tadi" - shuni hisobga oladi.
    """
    when = when or datetime.datetime.now()
    hour = when.hour
    if NIGHT_START_HOUR > DAY_START_HOUR:
        return hour >= NIGHT_START_HOUR or hour < DAY_START_HOUR
    return NIGHT_START_HOUR <= hour < DAY_START_HOUR


async def get_pricing_center() -> tuple[float, float]:
    """Admin xaritadan belgilagan markazni qaytaradi. Hali hech kim
    belgilamagan bo'lsa, config.py dagi eski STORE_LAT/STORE_LON ishlatiladi
    (shuning uchun admin panelsiz ham loyiha ishlayveradi)."""
    async with async_session() as session:
        result = await session.execute(select(PricingCenter).order_by(PricingCenter.updated_at.desc()).limit(1))
        center = result.scalar_one_or_none()
    if center:
        return center.lat, center.lon
    return STORE_LAT, STORE_LON


async def set_pricing_center(lat: float, lon: float, label: str | None = None) -> None:
    async with async_session() as session:
        session.add(PricingCenter(lat=lat, lon=lon, label=label))
        await session.commit()


async def get_active_bands(order_type: str) -> list[DistanceBand]:
    async with async_session() as session:
        result = await session.execute(
            select(DistanceBand)
            .where(DistanceBand.order_type == order_type, DistanceBand.is_active.is_(True))
            .order_by(DistanceBand.min_km.asc())
        )
        return list(result.scalars().all())


def _find_band(bands: list[DistanceBand], distance_km: float) -> DistanceBand | None:
    for band in bands:
        if distance_km >= band.min_km and (band.max_km is None or distance_km < band.max_km):
            return band
    return None


async def calculate_zone_price(
    distance_km: float | None,
    order_type: str,
    pickup_lat: float | None = None,
    pickup_lon: float | None = None,
    when: datetime.datetime | None = None,
) -> tuple[float, int | None]:
    """Admin panelda sozlangan diapazonlarga qarab narxni hisoblaydi.

    Masofa markazdan (admin xaritada belgilagan nuqtadan) hisoblanadi -
    talabga ko'ra ("o'rta masofani xaritadan admin belgilasin"). Agar hali
    hech qanday diapazon sozlanmagan bo'lsa, (None, None) qaytaradi - bu holda
    chaqiruvchi eski pricing.py formulasiga qaytishi kerak (backward compat).
    """
    bands = await get_active_bands(order_type)
    if not bands:
        return None, None

    center_lat, center_lon = await get_pricing_center()

    # Diapazonni aniqlash uchun ishlatiladigan masofa: agar pickup nuqtasi
    # berilgan bo'lsa - markazdan pickup'gacha bo'lgan masofa (qay diapazonda
    # ekanini bilish uchun); narxni hisoblash uchun esa haqiqiy safar
    # masofasi (distance_km) ishlatiladi.
    if pickup_lat is not None and pickup_lon is not None:
        band_distance = haversine_km(center_lat, center_lon, pickup_lat, pickup_lon)
    elif distance_km is not None:
        band_distance = distance_km
    else:
        band_distance = 0.0

    band = _find_band(bands, band_distance)
    if band is None:
        band = bands[-1]  # eng uzoq diapazonga tushirib qo'yamiz (cheksiz variant)

    night = is_night(when)
    base_fare = band.night_base_fare if night else band.day_base_fare
    price_per_km = band.night_price_per_km if night else band.day_price_per_km
    min_fare = band.night_min_fare if night else band.day_min_fare

    km_for_price = distance_km if distance_km is not None else band_distance
    price = base_fare + price_per_km * km_for_price
    price = max(price, min_fare)
    return round(price, -2), band.id


async def get_demand_by_band(order_type: str, hours: int = 3) -> list[tuple[DistanceBand, int]]:
    """Haydovchi uchun: so'nggi `hours` soatda qaysi diapazonda (masofa
    zonasida) buyurtmalar ko'proq tushayotganini hisoblaydi - "talab
    xaritasi"."""
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    bands = await get_active_bands(order_type)
    if not bands:
        return []
    async with async_session() as session:
        result = await session.execute(
            select(Order.distance_band_id).where(
                Order.order_type == order_type,
                Order.created_at >= since,
                Order.distance_band_id.is_not(None),
            )
        )
        band_ids = [row[0] for row in result.all()]
    counts = {band.id: 0 for band in bands}
    for band_id in band_ids:
        if band_id in counts:
            counts[band_id] += 1
    ranked = sorted(bands, key=lambda b: counts.get(b.id, 0), reverse=True)
    return [(band, counts.get(band.id, 0)) for band in ranked]
