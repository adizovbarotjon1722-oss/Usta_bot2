from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import FLOOD_BAN_THRESHOLD, FLOOD_BLOCK_SECONDS, FLOOD_MAX_MESSAGES, FLOOD_WINDOW_SECONDS

# ---------------------------------------------------------------------------
# Anti-flood / anti-spam
# ---------------------------------------------------------------------------
# Eslatma: bu himoya jarayon xotirasida (in-memory) ishlaydi. Bitta server
# jarayonida (hozirgi arxitekturada shunday) yetarli. Agar kelajakda botni
# bir nechta jarayon/server sifatida ishga tushirsangiz, buni Redis kabi
# umumiy xotiraga ko'chirish tavsiya etiladi.

_message_times: dict[int, deque[float]] = defaultdict(deque)
_blocked_until: dict[int, float] = {}
_strike_count: dict[int, int] = defaultdict(int)

# Bloklangan (butunlay ban qilingan) foydalanuvchilar shu jarayon davomida
# xotirada saqlanadi; doimiy ban uchun User.is_banned / Driver.is_blocked
# maydonlaridan (databasega yoziladi) foydalaning.
PERMANENTLY_FLAGGED: set[int] = set()


def register_flood_strike(user_id: int) -> int:
    _strike_count[user_id] += 1
    return _strike_count[user_id]


class AntiFloodMiddleware(BaseMiddleware):
    """Bir foydalanuvchi juda tez-tez xabar/callback yuborsa (spam/bot-hujum),
    vaqtincha e'tiborga olinmaydi. Ko'p marta takrorlansa, doimiy belgilanadi
    (PERMANENTLY_FLAGGED) - bot logikasi buni ko'rib, foydalanuvchini
    bazada ham bloklashi mumkin."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        user_id = user.id
        now = time.monotonic()

        if user_id in PERMANENTLY_FLAGGED:
            return None  # jimgina e'tiborsiz qoldiriladi

        blocked_till = _blocked_until.get(user_id)
        if blocked_till and now < blocked_till:
            return None
        if blocked_till and now >= blocked_till:
            _blocked_until.pop(user_id, None)

        window = _message_times[user_id]
        window.append(now)
        while window and now - window[0] > FLOOD_WINDOW_SECONDS:
            window.popleft()

        if len(window) > FLOOD_MAX_MESSAGES:
            window.clear()
            _blocked_until[user_id] = now + FLOOD_BLOCK_SECONDS
            strikes = register_flood_strike(user_id)
            if strikes >= FLOOD_BAN_THRESHOLD:
                PERMANENTLY_FLAGGED.add(user_id)
                data["flood_permanent_ban"] = True
            else:
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Juda tez-tez xabar yubordingiz. Iltimos, "
                            f"{int(FLOOD_BLOCK_SECONDS)} soniya kutib turing."
                        )
                    except Exception:
                        pass
            return None

        return await handler(event, data)


# ---------------------------------------------------------------------------
# Validatsiya yordamchilari
# ---------------------------------------------------------------------------

# O'zbekiston taxminiy geografik chegaralari - GPS spoofing/xato joylashuvni
# to'liq oldini olmasa-da, aniq bo'lmagan qiymatlarni (masalan 0,0) ushlab
# qoladi.
_UZ_LAT_RANGE = (37.0, 46.0)
_UZ_LON_RANGE = (55.0, 74.0)


def is_plausible_coordinate(lat: float | None, lon: float | None, *, strict_uzbekistan: bool = False) -> bool:
    if lat is None or lon is None:
        return False
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return False
    if lat == 0.0 and lon == 0.0:
        return False
    if strict_uzbekistan:
        return _UZ_LAT_RANGE[0] <= lat <= _UZ_LAT_RANGE[1] and _UZ_LON_RANGE[0] <= lon <= _UZ_LON_RANGE[1]
    return True


def mask_phone(phone: str | None) -> str:
    """Loglarda/admin xabarlarida telefon raqamini qisman yashirish uchun
    (masalan +998901234567 -> +998******567)."""
    if not phone:
        return "-"
    digits = phone.strip()
    if len(digits) <= 6:
        return "*" * len(digits)
    return digits[:4] + "*" * (len(digits) - 7) + digits[-3:]


def sanitize_free_text(text: str | None, max_len: int = 512) -> str:
    """Foydalanuvchi kiritgan erkin matnni (manzil, mahsulot nomi va h.k.)
    xavfsiz uzunlikka qisqartiradi va boshqaruvchi belgilarni tozalaydi
    (admin panelda/log'larda ko'rsatilganda muammo tug'dirmasligi uchun)."""
    if not text:
        return ""
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    return cleaned.strip()[:max_len]
