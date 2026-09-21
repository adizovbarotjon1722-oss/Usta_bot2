# Telegram taksi + yetkazib berish xizmati (MVP)

O'zbekistonning chekka viloyatlari uchun Telegram orqali ishlaydigan taksi va
yetkazib berish xizmati. Ikkita alohida bot ishlatiladi: mijozlar uchun va
haydovchi/kuryerlar uchun.

## Ishlaydigan funksiyalar

- **Mijoz boti**: ro'yxatdan o'tish, taksi buyurtma qilish, yetkazib berish
  buyurtma qilish, buyurtmalar tarixini ko'rish
- **Masofaga qarab dinamik narxlash**: foydalanuvchi joylashuvini (GPS)
  yuborsa, narx haqiqiy masofaga qarab hisoblanadi (bazaviy narx + km narxi,
  minimal narx bilan chegaralangan). Agar GPS yubormay, manzilni qo'lda yozsa
  — qat'iy (flat) narx ko'rsatiladi. Bu ikkalasi ham ishlaydi, chunki chekka
  hududlarda ba'zi foydalanuvchilarning GPS'i yoki internet aloqasi zaif
  bo'lishi mumkin.
- **Web admin panel** (`admin_panel/`): brauzer orqali kirib, haydovchilarni
  tasdiqlash/bloklash, barcha buyurtmalarni kuzatish va bekor qilish,
  mijozlar ro'yxatini ko'rish mumkin. Parol bilan himoyalangan.
- **Payme va Click orqali onlayn to'lov** (`payments/`): mijoz buyurtma
  bergach, xohlasa Payme yoki Click tugmasi orqali onlayn to'lashi mumkin.
  To'lov holati bazada va admin panelda kuzatiladi. `.env` da
  `PAYME_MERCHANT_ID`/`CLICK_MERCHANT_ID` bo'sh qoldirilsa, bu tugmalar
  ko'rsatilmaydi va hamma narsa avvalgidek naqd to'lov bilan ishlayveradi.
- **Haydovchi boti**: ro'yxatdan o'tish (hujjat + selfi rasmi bilan — shaxsni
  tasdiqlash uchun), admin tomonidan tasdiqlash, onlayn/oflayn holat,
  buyurtmani qabul/rad etish, safar bosqichlari (yetib keldim → bajarildi)
- **Admin**: yangi haydovchi ro'yxatdan o'tganda avtomatik xabar oladi va
  `/approve <id>` buyrug'i orqali tasdiqlaydi
- **Ikki tillilik (o'zbek/rus)**: mijoz boti `/start`da til tanlashni so'raydi
  va shu tilda davom etadi (`translations.py`)
- **Referal va bonus tizimi**: har bir mijoz o'zining referal havolasiga ega;
  taklif qilingan do'sti birinchi buyurtmasini yakunlasa, taklif qiluvchiga
  bonus balans qo'shiladi (keyingi buyurtmalarda avtomatik ishlatiladi)
- **Promo-kodlar**: admin panelda yaratiladi, mijoz buyurtma berishda kiritishi
  mumkin, foiz bo'yicha chegirma beradi
- **Komissiya tizimi**: har bir yakunlangan buyurtmadan platforma komissiyasi
  hisoblanadi va haydovchining "qarzi" sifatida kuzatiladi; admin panelda
  qarzni "yopish" mumkin
- **Talab bo'yicha narxlash (surge)**: admin panelda bitta koeffitsient orqali
  barcha yangi buyurtmalar narxini vaqtincha oshirish mumkin
- **Bir nechta do'kon/filial**: agar bir nechta hududda ishlasangiz, admin
  panelda qo'shimcha nuqtalar qo'shish mumkin — mijoz yetkazib berish
  buyurtmasida qaysi nuqtadan olib ketishni tanlaydi
- **Rejalashtirilgan buyurtma**: mijoz "hozir" yoki kelajakdagi aniq vaqtga
  buyurtma berishi mumkin; fon vazifasi (`main.py`) belgilangan vaqt kelganda
  avtomatik haydovchi qidirishni boshlaydi
- **Bekor qilish siyosati**: mijoz o'z buyurtmasini (hali qabul qilinmagan
  bo'lsa) bekor qila oladi; so'nggi 24 soatda 3 martadan ko'p bekor qilsa,
  vaqtincha yangi buyurtma berolmaydi (`config.py` da sozlanadi)
- **SOS tugmasi**: faol buyurtma davomida mijoz yoki haydovchi bosishi mumkin
  — barcha adminlarga darhol xabar boradi, admin panelda SOS jurnali saqlanadi
- **Jonli xarita kuzatuvi**: haydovchi Telegram'ning "Jonli joylashuv" (Share
  Live Location) funksiyasini yoqsa, mijoz uni xaritada real vaqtda ko'rib
  boradi
- **Ommaviy xabar (broadcast)**: admin paneldan barcha mijozlarga yoki barcha
  haydovchilarga bir vaqtda xabar yuborish mumkin
- **Xatolarni kuzatish (Sentry)**: `.env` da `SENTRY_DSN` to'ldirilsa,
  botlardagi kutilmagan xatolar avtomatik Sentry'ga yuboriladi (ixtiyoriy)
- **Avtomatik testlar** (`tests/`): narxlash va komissiya/chegirma
  hisob-kitoblari `pytest` orqali tekshiriladi — `pytest tests/`
- **Diapazon (zona) narxlash**: admin panelda interaktiv xaritada narx
  markazini belgilash, undan masofa bo'yicha diapazonlar (masalan 0-5 km,
  5-10 km) uchun kunduzgi/kechgi qat'iy narx belgilash mumkin — sozlansa,
  taksi narxi shu jadvaldan avtomatik olinadi
- **"Ochiq marshrut"** — mijoz aniq manzilni oldindan aytmasdan, yo'l
  davomida haydovchiga o'zi yo'l ko'rsatib boradigan safar turi; narx
  vaqt (daqiqa) asosida hisoblanadi
- **Birinchi buyurtma chegirmasi** — yangi mijozning birinchi buyurtmasiga
  avtomatik foizli chegirma qo'llanadi
- **Haydovchi uchun "Band hududlar"** — so'nggi soatlardagi buyurtmalar
  qaysi diapazonda ko'pligini ko'rsatadi
- **Mijozlarni ham bloklash imkoniyati** (avval faqat haydovchilar
  bloklanardi) — suiiste'mol qiluvchi foydalanuvchilarni to'xtatish uchun
- Ma'lumotlar SQLite bazasida saqlanadi (`bot.db` fayli avtomatik yaratiladi)

## O'rnatish

1. Python 3.11+ o'rnatilgan bo'lishi kerak.
2. Kutubxonalarni o'rnating:

   ```bash
   pip install -r requirements.txt
   ```

3. `@BotFather` orqali **ikkita** bot yarating (masalan
   `MentaTaksi_bot` va `MentaHaydovchi_bot`) va tokenlarni oling.

4. `.env.example` faylini `.env` deb nusxalang va tokenlaringizni kiriting:

   ```bash
   cp .env.example .env
   ```

   `.env` faylida:

   ```
   CLIENT_BOT_TOKEN=...
   DRIVER_BOT_TOKEN=...
   ADMIN_IDS=123456789
   ```

   `ADMIN_IDS` — sizning shaxsiy Telegram ID raqamingiz (bir nechta bo'lsa
   vergul bilan ajrating). ID raqamingizni bilish uchun Telegram'da
   `@userinfobot` ga yozing.

   `ADMIN_PANEL_PASSWORD` va `ADMIN_PANEL_SECRET_KEY` — web admin panelga
   kirish uchun parol va sessiya kaliti. Ikkalasini ham standart qiymatdan
   almashtiring.

5. Botlarni ishga tushiring:

   ```bash
   python main.py
   ```

Ikkala bot bir vaqtda ishlay boshlaydi.

## Web admin panelni ishga tushirish

Bot va admin panel **alohida-alohida** ishga tushiriladi (ikkita alohida
terminal oynasida):

```bash
uvicorn admin_panel.app:app --reload --port 8000
```

So'ng brauzerda `http://localhost:8000` manzilini oching, `.env` faylidagi
`ADMIN_PANEL_PASSWORD` bilan kiring. Bu yerdan:

- Yangi haydovchilarni tasdiqlashingiz yoki rad etishingiz,
- Muammoli haydovchilarni bloklashingiz,
- Barcha buyurtmalarni holati bo'yicha ko'rishingiz va kerak bo'lsa bekor
  qilishingiz,
- Mijozlar ro'yxatini ko'rishingiz mumkin.

Bot va admin panel bitta bazani (`bot.db`) baham ko'radi — ikkalasi ham bir
vaqtda ishlab tursa, o'zgarishlar darhol ikkalasida ham ko'rinadi.

## To'lov serverini mahalliy sinash

To'lov webhook serveri ham alohida ishga tushiriladi:

```bash
uvicorn payments_server:app --reload --port 8001
```

Bu server faqat Payme/Click'ning o'zi tashqaridan chaqirganda foydali —
mahalliy kompyuteringizda ishga tushirilsa, tashqi internetdan
ko'rinmaydi (buning uchun `ngrok` kabi vosita yoki production serverga
joylashtirish kerak, qarang: `DEPLOY.md`). Mahalliyda faqat kodning
xatosiz ishga tushishini tekshirish uchun foydali.

## Mobil ilova (Flutter, Play Market uchun)

Telegram botdan tashqari, alohida **mobil ilova** (`mobile_app/`) ham
tayyorlanmoqda — bu Play Market'ga chiqarish mumkin bo'lgan haqiqiy Android
ilova bo'ladi. U `api_server.py` orqali ishlaydigan REST API bilan
gaplashadi va Telegram bot bilan bitta bazani baham ko'radi.

To'liq o'rnatish va Play Market'ga chiqarish qo'llanmasi:
**`mobile_app/README.md`**

API serverni mahalliy ishga tushirish:

```bash
uvicorn api_server:app --reload --port 8002
```

## Sinab ko'rish

1. Haydovchi botiga o'zingiz kirib `/start` bosing, ro'yxatdan o'ting va
   hujjat rasmini yuboring (istalgan rasm bo'lishi mumkin, demo uchun).
2. Admin sifatida sizga xabar keladi — `/approve <driver_id>` yuboring.
3. Haydovchi botida "✅ Onlayn" tugmasini bosing.
4. Boshqa Telegram akkaunt bilan (yoki shu akkauntning o'zi bilan, agar test
   qilayotgan bo'lsangiz) mijoz botiga kirib buyurtma bering.
5. Haydovchi botida buyurtma taklifi keladi — qabul qiling va bosqichma-bosqich
   yakunlang.

## Loyihaning tuzilishi

```
config.py       - sozlamalar, narxlash koeffitsientlari
database.py     - SQLAlchemy modellari (User, Driver, Order)
matching.py     - mos haydovchini topish logikasi
pricing.py      - narx formulasi va taxminiy (haversine) masofa hisoblash
routing.py      - OSRM orqali haqiqiy yo'l masofasini so'rash
client_bot.py   - mijoz boti (ro'yxat, buyurtma berish)
driver_bot.py   - haydovchi boti (ro'yxat, qabul/rad, admin tasdiqlash)
main.py         - ikkala botni birga ishga tushirish
admin_panel/    - web admin panel (FastAPI)
  app.py        - sahifalar va amallar (tasdiqlash, bloklash, bekor qilish)
  templates/    - HTML shablonlar (Jinja2)
  static/       - CSS
payments/       - Payme va Click integratsiyasi
  payme.py      - Payme Merchant API (JSON-RPC webhook)
  click.py      - Click Shop API (prepare/complete webhook)
payments_server.py - to'lov webhooklarini qabul qiluvchi ochiq server
api_server.py   - mobil ilova (Flutter) uchun REST API
mobile_auth.py  - telefon+SMS orqali kirish (OTP, JWT token)
sms.py          - SMS yuborish (Eskiz.uz, dev rejimda logga yozadi)
mobile_app/     - Flutter mobil ilova (Play Market uchun)
deploy/         - production uchun systemd va nginx konfiguratsiyalari
DEPLOY.md       - serverga joylashtirish bo'yicha to'liq qo'llanma
SECURITY.md     - amalga oshirilgan xavfsizlik choralari ro'yxati
PRIVACY.md      - maxfiylik siyosati (mijoz va haydovchilar uchun)
```

### Narxlash qanday ishlaydi

Ikkala nuqta ham GPS orqali kelganda, `routing.py` **OSRM** xizmatiga
so'rov yuborib haqiqiy yo'l masofasini oladi (asfalt yo'llar, burilishlar
hisobga olingan holda). Agar bu so'rov muvaffaqiyatsiz bo'lsa (internet
uzilishi, xizmat javob bermasligi) — avtomatik ravishda `pricing.py` dagi
to'g'ri chiziq + koeffitsient asosidagi taxminiy formulaga o'tadi.
Foydalanuvchi buni sezmaydi, narx baribir ko'rsatiladi.

Keyin narx formulasi ishga tushadi:

```
narx = bazaviy_narx + (masofa_km * km_narxi)
narx = max(narx, minimal_narx)
```

Barcha koeffitsientlar `config.py` da (`BASE_FARE_TAXI`,
`PRICE_PER_KM_TAXI`, `MIN_FARE_TAXI` va delivery uchun mos nomlar) — bozor
sharoitiga qarab sozlang. Yetkazib berish uchun boshlang'ich nuqta
`STORE_LAT`/`STORE_LON` orqali belgilanadi (hozircha bitta nuqta — bir nechta
do'kon bo'lsa, buni kengaytirish kerak bo'ladi).

**OSRM haqida muhim eslatma:** standart holatda OSRM'ning bepul, ommaviy
demo serveri ishlatiladi (`router.project-osrm.org`) — bu faqat **sinov**
uchun yaroqli, chunki tezlik va ishlash vaqti kafolatlanmaydi va yuqori
yuklamada bloklanishi mumkin. Production uchun o'zingizning OSRM
serveringizni Docker orqali ko'taring (O'zbekiston hududi uchun OpenStreetMap
ma'lumotlari bilan) va `.env` faylida `OSRM_BASE_URL` ni shunga
yo'naltiring:

```
OSRM_BASE_URL=http://localhost:5000
```

## Production serverga joylashtirish

To'liq qo'llanma uchun **`DEPLOY.md`** fayliga qarang — VPS tanlashdan
tortib, `systemd` xizmatlari, `nginx` + SSL, va avtomatik zaxira nusxagacha
bosqichma-bosqich yoritilgan. Tayyor konfiguratsiya fayllari `deploy/`
papkasida.

## Keyingi qadamlar (production uchun tavsiyalar)

- **O'z OSRM serveringizni ko'tarish**: yuqoridagi eslatmaga qarang — bu eng
  muhim production tayyorgarlik qadamlaridan biri.
- **To'lov**: hozir faqat "naqd" deb belgilanadi. Payme/Click API
  integratsiyasini qo'shish kerak.
- **Geolokatsiya**: hozir manzillar matn sifatida kiritiladi. Telegram
  location xabarlarini qabul qilib, PostGIS orqali "eng yaqin haydovchi"
  logikasini qo'shish mumkin.
- **Baza**: yuklama oshganda SQLite'dan PostgreSQL'ga o'ting — buning uchun
  faqat `DATABASE_URL` ni o'zgartirish va `asyncpg` kutubxonasini o'rnatish
  kifoya, kod o'zgarishsiz ishlaydi.
- **Reyting tizimi**: buyurtma yakunlangach mijoz 1-5 oralig'ida baho beradi,
  bu bazaga yoziladi va haydovchining o'rtacha reytingi (`Driver.rating`)
  avtomatik yangilanadi.
