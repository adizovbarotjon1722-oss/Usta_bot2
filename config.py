import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# Ikkita alohida Telegram bot: biri mijozlar uchun, biri haydovchi/kuryerlar uchun.
# Har birini @BotFather orqali yarating va tokenlarni .env fayliga qo'ying.
CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN", "")
DRIVER_BOT_TOKEN = os.getenv("DRIVER_BOT_TOKEN", "")

# Standart holatda SQLite ishlatiladi - hech qanday sozlashsiz ishlaydi.
# Productionda PostgreSQL'ga o'tish uchun shu qatorni o'zgartiring, masalan:
# postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

# Admin bo'lgan foydalanuvchilarning Telegram ID raqamlari (vergul bilan ajratilgan)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Web admin panelga kirish uchun parol va sessiya imzolash kaliti.
# Ikkalasini ham productionda uzun, tasodifiy qiymatlarga almashtiring.
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "changeme")
ADMIN_PANEL_SECRET_KEY = os.getenv("ADMIN_PANEL_SECRET_KEY", "dev-secret-key-please-change")

# Haydovchi buyurtmaga javob berishi kerak bo'lgan vaqt (soniyalarda)
ORDER_RESPONSE_TIMEOUT = 30

# Foydalanuvchi joylashuv (GPS) yubormasa, shu qat'iy narxlar ishlatiladi.
TAXI_FLAT_PRICE = 15000
DELIVERY_FLAT_PRICE = 10000

# Masofaga asoslangan dinamik narxlash (ikkala tomon ham GPS yuborsa ishlaydi).
# Narxlar so'mda, masofa kilometrda.
BASE_FARE_TAXI = 5000
PRICE_PER_KM_TAXI = 2000
MIN_FARE_TAXI = 10000

BASE_FARE_DELIVERY = 5000
PRICE_PER_KM_DELIVERY = 1500
MIN_FARE_DELIVERY = 8000

# To'g'ri chiziq masofasini haqiqiy yo'l masofasiga yaqinlashtirish uchun
# taxminiy koeffitsient (yo'llar to'g'ri chiziq bo'lmagani uchun).
# Aniqroq natija uchun Yandex Router API yoki OSRM kabi xizmatni ulash tavsiya etiladi.
ROAD_DISTANCE_FACTOR = 1.3

# Yetkazib berish uchun boshlang'ich nuqta (masalan, hudud markazi yoki asosiy ombor).
# TODO: har bir do'kon/hudud uchun alohida joylashuv qo'shish kerak bo'ladi.
STORE_LAT = 41.311081
STORE_LON = 69.240562

# Haqiqiy yo'l masofasini hisoblash uchun OSRM xizmati (ochiq kodli, bepul).
# Standart holatda OSRM'ning ommaviy demo serveri ishlatiladi - bu faqat sinov
# uchun yaroqli (tezlik va ishonchlilik kafolatlanmaydi). Productionda albatta
# o'zingizning OSRM serveringizni ko'taring (Docker orqali oson) va shu yerga
# uning manzilini yozing, masalan: OSRM_BASE_URL=http://localhost:5000
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")
ROUTING_TIMEOUT_SECONDS = 5

# Payme sozlamalari - https://business.payme.uz Merchant kabinetidan olinadi.
# PAYME_SECRET_KEY - "Kassa sozlamalari" > "Amaliy" bo'limidagi maxfiy kalit.
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "")

# Click sozlamalari - https://my.click.uz Merchant kabinetidan olinadi.
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")

# Platforma har bir yakunlangan buyurtmadan shu foizni komissiya sifatida
# oladi (haydovchi/kuryerning balansiga "qarz" sifatida yoziladi).
PLATFORM_COMMISSION_PERCENT = float(os.getenv("PLATFORM_COMMISSION_PERCENT", "15"))

# Do'st taklif qilgan (referal) foydalanuvchi birinchi buyurtmasini
# yakunlaganda, taklif qilgan kishining bonus balansiga shuncha so'm qo'shiladi.
REFERRAL_BONUS_AMOUNT = float(os.getenv("REFERRAL_BONUS_AMOUNT", "5000"))
# Yangi mijozning birinchi buyurtmasiga avtomatik chegirma (foizda, 0 = o'chirilgan)
FIRST_ORDER_DISCOUNT_PERCENT = float(os.getenv("FIRST_ORDER_DISCOUNT_PERCENT", "15"))

# "Ochiq marshrut" (mijoz yo'l ko'rsatib boradigan) safar uchun - narx aniq
# masofa emas, safar davomiyligiga (daqiqaga) qarab hisoblanadi.
OPEN_ROUTE_BASE_FARE = float(os.getenv("OPEN_ROUTE_BASE_FARE", "5000"))
OPEN_ROUTE_PRICE_PER_MINUTE = float(os.getenv("OPEN_ROUTE_PRICE_PER_MINUTE", "1000"))
OPEN_ROUTE_MIN_FARE = float(os.getenv("OPEN_ROUTE_MIN_FARE", "10000"))

# Rejalashtirilgan buyurtmalarni necha soniyada bir tekshirib, haydovchilarga
# yuborish kerakligini belgilaydi (background vazifa uchun, main.py'ga qarang).
SCHEDULED_ORDER_CHECK_INTERVAL_SECONDS = 60

# Mijoz shu vaqt oralig'ida (soatlarda) shu sondan ko'p buyurtmani o'zi bekor
# qilsa, yangi buyurtma berishdan vaqtincha to'xtatiladi (haydovchilarni
# behuda urinishlardan himoya qilish uchun).
CANCEL_LIMIT = int(os.getenv("CANCEL_LIMIT", "3"))
CANCEL_WINDOW_HOURS = int(os.getenv("CANCEL_WINDOW_HOURS", "24"))

# Xatolarni kuzatish (https://sentry.io). Bo'sh qoldirilsa, Sentry yoqilmaydi.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# ---------------------------------------------------------------------------
# Mobil ilova uchun autentifikatsiya (telefon + SMS-kod, JWT token)
# ---------------------------------------------------------------------------

# Tokenlarni imzolash kaliti - production'da albatta uzun, tasodifiy qiymatga almashtiring:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-please-change")
JWT_EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", "30"))

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
# Bitta kod uchun ruxsat etilgan noto'g'ri urinishlar soni - shundan ko'p
# xato kiritilsa, kod bloklanadi va yangisini so'rash kerak bo'ladi.
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
# Bitta telefon raqami uchun yangi kod so'rashlar orasidagi minimal vaqt
# (soniyada) - SMS-bombardimon va xarajatlarni suiiste'mol qilishdan himoya.
OTP_REQUEST_COOLDOWN_SECONDS = int(os.getenv("OTP_REQUEST_COOLDOWN_SECONDS", "60"))

# SMS xizmati (masalan, Eskiz.uz - O'zbekistonda keng tarqalgan). Bo'sh qoldirilsa,
# SMS yuborilmaydi - kod o'rniga javobda "dev_code" sifatida qaytariladi, shunda
# haqiqiy SMS xizmatisiz ham mahalliy sinash mumkin bo'ladi.
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "")  # "" yoki "eskiz"
SMS_API_EMAIL = os.getenv("SMS_API_EMAIL", "")
SMS_API_PASSWORD = os.getenv("SMS_API_PASSWORD", "")
SMS_SENDER_NAME = os.getenv("SMS_SENDER_NAME", "4546")

