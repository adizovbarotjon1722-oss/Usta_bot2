from __future__ import annotations

import logging

import aiohttp

from config import OSRM_BASE_URL, ROUTING_TIMEOUT_SECONDS
from pricing import estimate_road_distance_km

logger = logging.getLogger(__name__)


async def get_route_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """OSRM xizmati orqali haqiqiy yo'l masofasini (km) so'raydi.

    Agar xizmat javob bermasa, vaqt tugasa yoki internet aloqasi uzilsa
    (chekka hududlarda bu ehtimoli yuqori), to'g'ri chiziq masofasi +
    koeffitsient asosidagi taxminiy formulaga qaytadi. Shuning uchun bu
    funksiya hech qachon xato bilan to'xtamaydi - foydalanuvchi doim narxni
    ko'radi, ishonchli internet bo'lmasa ham.
    """
    url = f"{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        timeout = aiohttp.ClientTimeout(total=ROUTING_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"OSRM javobi: {resp.status}")
                data = await resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    raise RuntimeError("OSRM: marshrut topilmadi")
                distance_m = data["routes"][0]["distance"]
                return distance_m / 1000
    except Exception as exc:  # noqa: BLE001 - istalgan xatoda taxminiy formulaga o'tamiz
        logger.warning("OSRM so'rovi muvaffaqiyatsiz (%s) - taxminiy masofa ishlatilmoqda", exc)
        return estimate_road_distance_km(lat1, lon1, lat2, lon2)
