from __future__ import annotations

from sqlalchemy import select

from database import Driver, async_session


async def find_available_driver(vehicle_type: str | None = None) -> Driver | None:
    """Eng yaqin emas, lekin oddiy: onlayn, tasdiqlangan va eng yuqori reytingli
    haydovchini topadi. Kelajakda geolokatsiya asosida "eng yaqin" mantiqqa
    almashtirish uchun shu funksiyani kengaytiring (masalan PostGIS yordamida).
    """
    async with async_session() as session:
        stmt = select(Driver).where(Driver.status == "online", Driver.is_approved.is_(True))
        if vehicle_type:
            stmt = stmt.where(Driver.vehicle_type == vehicle_type)
        stmt = stmt.order_by(Driver.rating.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
