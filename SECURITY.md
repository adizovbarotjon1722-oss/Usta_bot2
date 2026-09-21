# Xavfsizlik choralari

Bu loyihada amalga oshirilgan xavfsizlik choralarining ro'yxati. Yangi
funksiya qo'shganda, shunga o'xshash tekshiruvlarni unutmang.

## 1. Buyurtma/ma'lumot egaligi (IDOR himoyasi)

Har bir amal (buyurtmani qabul qilish, rad etish, yakunlash, bekor qilish,
SOS) **ikki narsani** tekshiradi:
1. Amalni bajarayotgan odam kim ekanligi (haydovchi/mijoz sifatida
   ro'yxatdan o'tganmi)
2. Bu **aynan shu** buyurtma **aynan shu** odamga tegishlimi (va buyurtma
   holati mos keladigan bosqichdami)

Bular: `driver_bot.py` dagi `accept_order`, `decline_order`, `arrived`,
`complete_order`, `driver_sos`; `client_bot.py` dagi `cancel_own_order`,
`client_sos`; `api_server.py` dagi barcha `/orders/*` endpointlari.

**Yangi callback yoki API endpoint qo'shsangiz:** foydalanuvchi ID'sini
so'rovdan (callback_data, URL parametri) emas, balki autentifikatsiya
manbasidan (`callback.from_user.id`, JWT token) oling va bazadagi
`order.user_id`/`order.driver_id` bilan solishtiring.

## 2. OTP (SMS kod) himoyasi

- **Cooldown**: bitta telefon raqami uchun yangi kod `OTP_REQUEST_COOLDOWN_SECONDS`
  (standart 60s) dan tezroq so'ralmaydi — SMS-bombardimon va xarajat
  suiiste'molidan himoya
- **Urinishlar chegarasi**: bitta kod uchun `OTP_MAX_ATTEMPTS` (standart 5)
  dan ko'p noto'g'ri urinish bo'lsa, kod avtomatik bloklanadi — bruteforce
  orqali kod topishning oldini oladi
- **IP darajasida tezlik cheklovi**: `/auth/*` endpointlariga bitta IP
  daqiqasiga 10 tadan ortiq so'rov yubora olmaydi

## 3. JWT token

- Algoritm aniq ko'rsatilgan (`HS256`) — "alg=none" hujumidan himoya
- Token muddati cheklangan (`JWT_EXPIRY_DAYS`, standart 30 kun)
- `JWT_SECRET_KEY` production'da albatta uzun, tasodifiy qiymatga
  almashtirilishi kerak (`.env.example` da generatsiya buyrug'i bor)

## 4. Admin panel

- Parol solishtirish **vaqt-hujumiga chidamli** (`secrets.compare_digest`)
- Login urinishlari cheklangan: bitta IP 5 marta noto'g'ri parol kiritsa,
  5 daqiqaga bloklanadi
- Sessiya cookie: `https_only=True` (faqat HTTPS orqali), `same_site="strict"`
  (CSRF'dan asosiy himoya), 12 soatdan keyin avtomatik tugaydi
- Barcha sahifalar va amallar (`/drivers/*`, `/orders/*`, `/settings/*`,
  `/broadcast/*` va h.k.) `_logged_in()` tekshiruvidan o'tadi

## 5. To'lov webhooklari (Payme, Click)

- Payme: `Authorization: Basic` header orqali maxfiy kalit tekshiriladi
- Click: har bir so'rov MD5 imzosi orqali tasdiqlanadi
- Ikkalasi ham summani buyurtmadagi haqiqiy narx bilan solishtiradi (soxta
  kam summa bilan "to'landi" deb belgilashning oldini oladi)

## 6. Botlarda spam himoyasi

- `throttling.py`: bitta foydalanuvchidan soniyasiga bir nechta xabar/tugma
  kelsa, ortiqchasi jimgina e'tiborsiz qoldiriladi

## 7. Umumiy

- SQL so'rovlari barcha joyda SQLAlchemy ORM orqali (parametrlangan,
  SQL-in'ektsiyadan himoyalangan)
- Sentry'ga xato yuborilganda shaxsiy ma'lumotlar yuborilmaydi
  (`send_default_pii=False`)
- `.env` fayli hech qachon Git'ga yuklanmasligi kerak (`.env.example`
  faqat namuna)

## Bilib qo'yish kerak bo'lgan cheklovlar

- IP darajasidagi tezlik cheklovlari (`api_server.py`, `admin_panel/app.py`)
  xotirada ishlaydi — agar kelajakda bir nechta server nusxasi (masalan
  load balancer ortida) ishlatsangiz, bu cheklovlar har bir nusxada
  alohida hisoblanadi. Katta miqyosda Redis asosidagi yechimga o'ting.
- Admin panel uchun to'liq CSRF token tizimi emas, balki `SameSite=strict`
  cookie orqali himoya qilinadi — bu amaliyotda yetarli, lekin agar admin
  panelni boshqa domendan `<iframe>` yoki shunga o'xshash tarzda
  chaqirish kerak bo'lsa, bu yondashuvni qayta ko'rib chiqing.
