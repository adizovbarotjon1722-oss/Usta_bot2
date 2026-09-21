"""Yordamchi funksiyalar."""

from math import radians, sin, cos, sqrt, atan2


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Ikki koordinata orasidagi masofani km da hisoblaydi."""
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def estimate_eta_minutes(distance_km: float) -> int:
    """Masofaga qarab taxminiy yetib borish vaqtini (daqiqada) hisoblaydi."""
    from config import AVERAGE_SPEED_KMH
    if distance_km is None or distance_km == float("inf"):
        return None
    minutes = (distance_km / AVERAGE_SPEED_KMH) * 60
    return max(1, round(minutes))


def sort_masters_by_distance_and_rating(masters, cust_lat, cust_lon):
    """
    Ustalarni masofa (asosiy) va reyting (teng masofada bo'lsa) bo'yicha saralaydi.
    Har bir usta uchun masofani hisoblab, ro'yxat qaytaradi:
    [(master_row, distance_km), ...]
    """
    enriched = []
    for m in masters:
        dist = haversine_km(cust_lat, cust_lon, m["latitude"], m["longitude"])
        enriched.append((m, dist))
    enriched.sort(key=lambda pair: (round(pair[1], 1), -pair[0]["rating"]))
    return enriched


def filter_masters_within_radius(enriched_masters):
    """Faqat SEARCH_RADIUS_KM ichidagi ustalarni qoldiradi. Agar mijoz manzilini
    matn ko'rinishida kiritgan bo'lsa (masofa noma'lum, inf), radius bilan
    cheklamaymiz — chunki bu holda masofani solishtirib bo'lmaydi."""
    from config import SEARCH_RADIUS_KM
    result = []
    for m, dist in enriched_masters:
        if dist == float("inf") or dist <= SEARCH_RADIUS_KM:
            result.append((m, dist))
    return result


def has_permission(user_id: int, permission: str) -> bool:
    """Ko'p darajali admin huquqlarini tekshiradi.

    ⚠️ Xavfsizlik (tuzatildi): avval ADMIN_ROLES'da ko'rsatilmagan HAR
    QANDAY ADMIN_IDS a'zosi avtomatik "super" (cheklovsiz) hisoblanardi.
    Endi FAQAT SUPER_ADMIN_ID (config.py — standart bo'yicha ADMIN_IDS
    ro'yxatidagi birinchi ID) cheklovsiz; qolgan ADMIN_IDS a'zolari faqat
    ADMIN_ROLES'da ANIQ ko'rsatilgan ruxsatlarga ega, aks holda hech
    narsani o'zgartira olmaydi."""
    from config import ADMIN_IDS, ADMIN_ROLES, SUPER_ADMIN_ID
    if user_id == SUPER_ADMIN_ID:
        return True
    if user_id not in ADMIN_IDS:
        return False
    roles = ADMIN_ROLES.get(user_id) or []
    return "super" in roles or permission in roles


def is_super_admin(user_id: int) -> bool:
    """FAQAT yagona bosh admin. Boshqa adminlarni qo'shish/o'chirish yoki
    ularga rol berish kabi eng nozik amallar FAQAT shu foydalanuvchiga
    ruxsat etilishi kerak."""
    from config import SUPER_ADMIN_ID
    return SUPER_ADMIN_ID is not None and user_id == SUPER_ADMIN_ID


def get_local_now():
    """O'zbekiston mahalliy vaqtini qaytaradi (UTC + TIMEZONE_OFFSET_HOURS)."""
    from datetime import datetime, timedelta
    from config import TIMEZONE_OFFSET_HOURS
    return datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET_HOURS)


def is_master_available_now(master) -> bool:
    """Ustaning belgilangan ish vaqti bo'lsa, hozir shu oraliqda ekanini tekshiradi.
    Agar ish vaqti belgilanmagan bo'lsa (har doim ishlaydi), True qaytaradi."""
    start = master["work_hours_start"] if "work_hours_start" in master.keys() else None
    end = master["work_hours_end"] if "work_hours_end" in master.keys() else None
    if not start or not end:
        return True
    now_time = get_local_now().strftime("%H:%M")
    if start <= end:
        return start <= now_time <= end
    return now_time >= start or now_time <= end  # tungi smena (masalan 22:00-06:00)


def is_within_service_city(latitude, longitude) -> bool:
    """GPS koordinata xizmat ko'rsatiladigan shahar (Toshkent) chegarasida ekanini tekshiradi."""
    from config import TASHKENT_LAT_RANGE, TASHKENT_LON_RANGE
    if latitude is None or longitude is None:
        return True  # koordinata yo'q — bu tekshiruv matn manzili uchun emas
    lat_ok = TASHKENT_LAT_RANGE[0] <= latitude <= TASHKENT_LAT_RANGE[1]
    lon_ok = TASHKENT_LON_RANGE[0] <= longitude <= TASHKENT_LON_RANGE[1]
    return lat_ok and lon_ok


def validate_address_text(text: str) -> tuple:
    """Qo'lda yozilgan manzil yetarlicha aniq va shahar nomini o'z ichiga
    olganini tekshiradi. Qaytaradi: (to'g'rimi: bool, sabab_kaliti: str|None)."""
    from config import SERVICE_CITY_KEYWORDS
    if not text or len(text.strip()) < 10:
        return False, "too_short"
    lowered = text.lower()
    has_digit = any(ch.isdigit() for ch in text)
    if not has_digit:
        return False, "no_house_number"
    has_city = any(kw in lowered for kw in SERVICE_CITY_KEYWORDS)
    if not has_city:
        return False, "no_city"
    return True, None


async def notify_admins(bot, text: str, reply_markup=None):
    """Barcha adminlarga xabar yuborishga urinadi; admin botni bloklagan bo'lsa xatoni yutib yuboradi."""
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            pass


def format_order_line(order) -> str:
    from config import SERVICE_TYPES
    status_labels = {
        "searching": "🔍 Qidirilmoqda",
        "offered": "📨 Ustaga yuborildi",
        "pricing": "💬 Narx kutilmoqda",
        "offered_price": "💰 Narx taklif qilindi",
        "in_progress": "🚗 Bajarilmoqda",
        "done": "✅ Bajarildi",
        "cancelled": "❌ Bekor qilindi",
    }
    price_text = f"{order['price']:.0f} so'm" if order["price"] else "—"
    schedule_text = ""
    if "scheduled_at" in order.keys() and order["scheduled_at"]:
        schedule_text = f" | 📅 {order['scheduled_at']}"
    return (
        f"#{order['id']} | {SERVICE_TYPES.get(order['service_type'], order['service_type'])} | "
        f"{status_labels.get(order['status'], order['status'])} | {price_text}{schedule_text}"
    )


def format_master_line(m) -> str:
    from i18n import service_names_display
    status_labels = {
        "pending": "⏳ Kutilmoqda",
        "verified": "✅ Tasdiqlangan",
        "rejected": "❌ Rad etilgan",
        "blocked": "🚫 Bloklangan",
    }
    busy_text = "🔴 Band" if m["is_busy"] else "🟢 Bo'sh"
    extra = f", zaxira: {m['extra_phone']}" if m["extra_phone"] else ""
    age_exp = f" | {m['age'] or '—'} yosh, {m['experience_years'] or '—'} tajriba"
    return (
        f"#{m['id']} | {m['full_name']} | {m['phone']}{extra} | "
        f"{service_names_display(m['service_type'], 'uz')}{age_exp} | "
        f"{status_labels.get(m['status'], m['status'])} | {busy_text} | "
        f"⭐{m['rating']:.1f} | 💰{m['balance']:.0f} so'm"
    )


def format_customer_line(c) -> str:
    status = "🚫 Bloklangan" if c["blocked"] else "✅ Faol"
    return (
        f"#{c['id']} | {c['full_name'] or '(ism kiritilmagan)'} | "
        f"{c['phone'] or '(telefon yo`q)'} | ⭐{c['rating']:.1f} | {status}"
    )
