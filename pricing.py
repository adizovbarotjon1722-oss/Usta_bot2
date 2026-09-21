from __future__ import annotations

import math

from config import (
    BASE_FARE_DELIVERY,
    BASE_FARE_TAXI,
    DELIVERY_FLAT_PRICE,
    MIN_FARE_DELIVERY,
    MIN_FARE_TAXI,
    OPEN_ROUTE_BASE_FARE,
    OPEN_ROUTE_MIN_FARE,
    OPEN_ROUTE_PRICE_PER_MINUTE,
    PRICE_PER_KM_DELIVERY,
    PRICE_PER_KM_TAXI,
    ROAD_DISTANCE_FACTOR,
    TAXI_FLAT_PRICE,
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki geografik nuqta orasidagi to'g'ri chiziq masofasi (km)."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def estimate_road_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """To'g'ri chiziq masofasini taxminiy yo'l masofasiga aylantiradi.
    Aniqroq hisoblash uchun kelajakda Yandex Router / OSRM API bilan almashtiring."""
    return haversine_km(lat1, lon1, lat2, lon2) * ROAD_DISTANCE_FACTOR


def calculate_taxi_price(distance_km: float | None, surge_multiplier: float = 1.0) -> float:
    if distance_km is None:
        return round(TAXI_FLAT_PRICE * surge_multiplier, -2)
    price = (BASE_FARE_TAXI + PRICE_PER_KM_TAXI * distance_km) * surge_multiplier
    return round(max(price, MIN_FARE_TAXI * surge_multiplier), -2)  # eng yaqin 100 so'mga yaxlitlash


def calculate_delivery_price(distance_km: float | None, surge_multiplier: float = 1.0) -> float:
    if distance_km is None:
        return round(DELIVERY_FLAT_PRICE * surge_multiplier, -2)
    price = (BASE_FARE_DELIVERY + PRICE_PER_KM_DELIVERY * distance_km) * surge_multiplier
    return round(max(price, MIN_FARE_DELIVERY * surge_multiplier), -2)


def is_daytime(hour: int, day_start_hour: int, day_end_hour: int) -> bool:
    """Berilgan soat (0-23) kunduzgi oraliqqa tushadimi. day_start < day_end
    deb faraz qilinadi (masalan 7 dan 22 gacha kunduzgi)."""
    return day_start_hour <= hour < day_end_hour


def find_zone_price(distance_from_center_km: float, zones: list, is_day: bool) -> float | None:
    """Diapazonlar ro'yxatidan (min_km, max_km, day_price, night_price) mos
    kelganini topadi. Hech biriga to'g'ri kelmasa (masofa hammasidan katta
    yoki diapazon umuman sozlanmagan bo'lsa) None qaytaradi - shunda oddiy
    masofaviy formulaga qaytiladi."""
    for zone in sorted(zones, key=lambda z: z.min_km):
        if zone.min_km <= distance_from_center_km < zone.max_km:
            return zone.day_price if is_day else zone.night_price
    return None


def calculate_open_route_price(minutes: float, surge_multiplier: float = 1.0) -> float:
    """"Ochiq marshrut" (yo'l ko'rsatib boradigan) safar uchun - masofa emas,
    vaqt asosida narx hisoblaydi, chunki aniq marshrut oldindan noma'lum."""
    price = (OPEN_ROUTE_BASE_FARE + OPEN_ROUTE_PRICE_PER_MINUTE * max(minutes, 0)) * surge_multiplier
    return round(max(price, OPEN_ROUTE_MIN_FARE * surge_multiplier), -2)
