# Nima o'zgardi (so'rovlaringiz bo'yicha)

Har bir band sizning original xabaringizdagi raqamlarga mos keladi.

**1. Xavfsizlik va spamdan himoya** — `security.py` (yangi): flood/spam
himoyasi, GPS validatsiyasi, matn tozalash, telefon yashirish. Batafsil:
`SECURITY.md`. Payme/Click webhook imzosi tekshiruvi `payments/` manba kodi
kelgach tasdiqlanadi/qo'shiladi.

**2. Haydovchini faqat admin ro'yxatdan o'tqazishi** — Bu allaqachon deyarli
shunday ishlagan (haydovchi botga yozadi → admin `/approve` qiladi, shundan
keyingina "Onlayn" bo'la oladi). Men buni kuchaytirdim: endi transport
davlat raqami va shaxsni tasdiqlovchi hujjat seriya-raqami ham majburiy
so'raladi, va admin `/reject <id> <sabab>` bilan rad eta oladi (avval faqat
tasdiqlash bor edi).

**3. Joylashuv aniqligi va harakat strukturasi** — GPS koordinatalari endi
tekshiriladi (`is_plausible_coordinate`); haydovchi safar davomida yuborgan
har bir joylashuv `LocationPing` jadvaliga yoziladi — bu ham aniqlikni
oshiradi, ham #9-band ("o'zi yo'l ko'rsatish") uchun asos bo'ladi.

**4. Markazdan masofaga va kunduz/kecha vaqtiga qarab narxlash, admin
panel orqali** — Bazaviy tuzilma va hisoblash logikasi tayyor: `PricingCenter`
(admin xaritadan belgilaydigan markaz) va `DistanceBand` (har bir diapazon
uchun kunduzgi/kechgi bazaviy narx, km narxi, minimal narx). Bot avtomatik
shu jadvallardan foydalanadi; agar hali bo'sh bo'lsa, eski qat'iy formulaga
tushadi (buzilmaydi). **Admin panelning o'zi (xaritadan bosib belgilash
sahifasi) `admin_panel/` manba kodi kelgach qo'shiladi** — pastga qarang.

**5. Haydovchiga to'liq ma'lumot va taxminiy narx** — Yangi buyurtma taklifida
endi: buyurtma turi, masofa, taxminiy narx, to'lov usuli va (agar "o'zi yo'l
ko'rsatish" rejimi bo'lsa) alohida ogohlantirish ko'rsatiladi.

**6. Qaysi diapazonda buyurtma ko'pligini haydovchi ko'rishi** — "📊 Talab
zonalari" tugmasi qo'shildi — so'nggi 3 soatdagi buyurtmalarni diapazon
bo'yicha reytinglab ko'rsatadi.

**7. Mijoz paneli va dizayn** — Tasdiqlash endi tugmalar orqali (✅/❌), 
buyurtmalar tarixi holat-emoji bilan ko'rinadi, buyurtma turi tanlash yangi
tugmalar bilan chiroyliroq. **To'liq panel dizayni (admin panel HTML/CSS)
`admin_panel/` kodi kelgach yangilanadi.**

**8. Mijoz uchun chegirmali buyurtmalar** — Promo-kod tizimi allaqachon bor
edi; endi **birinchi buyurtmaga avtomatik chegirma** qo'shildi
(`FIRST_ORDER_DISCOUNT_PERCENT`, standart 10%, `.env`da o'zgartirish mumkin).

**9. Ikki xil buyurtma usuli** — Endi mijoz taksi chaqirganda tanlaydi:
"📍 Manzildan-manzilgacha" (avvalgidek) yoki "🧭 O'zim yo'l ko'rsataman"
(dropoff so'ralmaydi, haydovchi GPS trekiga qarab safar oxirida haqiqiy
narx hisoblanadi).

**10. Takliflar** — pastga qarang.

**11. Xavfsizlik va maxfiylik siyosati** — `/maxfiylik` (`/privacy`) buyrug'i
mijoz va haydovchi botlariga qo'shildi; to'liq nazorat ro'yxati
`SECURITY.md`da.

---

## 10-band: Loyihani yanada samarali qilish bo'yicha takliflar

1. **SQLite'dan PostgreSQL'ga o'tish** — bir nechta bot/server jarayoni va
   yuqori yuklama uchun kerak bo'ladi (`DATABASE_URL`ni o'zgartirish kifoya).
2. **Flood-himoyani Redis'ga ko'chirish** — hozirgi `security.py` bitta
   jarayon xotirasida ishlaydi; bir nechta serverga (worker) o'tsangiz umumiy
   xotira kerak bo'ladi.
3. **O'z OSRM serveringiz** — `README.md`da aytilganidek, hozir ommaviy
   demo server ishlatilmoqda, production uchun ishonchsiz.
4. **Push-xabar o'rniga real vaqtli xarita** — haydovchining joylashuvini
   mijozga (Telegram live location orqali) real vaqtda ko'rsatish safar
   ishonchini oshiradi.
5. **Haydovchi/mijoz uchun blokировка tarixi** — kim, qachon, nima sababdan
   bloklangani haqida audit jurnali (kelajakda kerak bo'lsa qo'shsa bo'ladi).
6. **Ikkala botni ham webhook rejimiga o'tkazish** (hozir polling) — VPS
   resursini tejaydi va Telegramning tavsiya etilgan rejimi.
7. **Promo-kodlarni muddatga bog'lash** (`valid_until`) — hozir faqat
   foiz/soni bilan cheklangan.

## Admin panel va payments uchun qolgan ish

`admin_panel/`, `payments/`, `deploy/` papkalari bo'sh yuklangani sababli,
ular ustida to'g'ridan-to'g'ri o'zgartirish kirita olmadim. Ularni alohida
zip qilib qayta yuborsangiz:

- Xaritadan markaz belgilash + diapazon narxlarini boshqarish sahifasini
  (`zones.py`dagi funksiyalarga ulab) qo'shaman.
- Payme/Click webhook imzosini tekshirish kodini ko'rib chiqaman/qo'shaman.
- Mijoz/haydovchi bloklash tugmalarini admin panelga qo'shaman.
- Panel dizaynini (#7) yangilayman.
