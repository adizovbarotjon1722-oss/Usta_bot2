# Production serverga joylashtirish qo'llanmasi

Bu qo'llanma Ubuntu 22.04/24.04 asosidagi VPS uchun yozilgan (eng ko'p
tarqalgan variant). Boshqa distributivlarda buyruqlar biroz farq qilishi
mumkin.

## 1. VPS tanlash

Minimal talab: **2 CPU, 2 GB RAM, 20 GB disk**. Bu botlar + admin panel +
kichik hajmdagi SQLite baza uchun yetarli. Agar o'z OSRM serveringizni ham
shu mashinada ishlatmoqchi bo'lsangiz, kamida **4 GB RAM** kerak bo'ladi.

CIS mintaqasida mashhur variantlar: Timeweb, Beget, Selectel. Xalqaro
variantlar: Hetzner, DigitalOcean. Narx-sifat nisbati bo'yicha Hetzner odatda
eng arzon (oyiga ~$4-5 dan boshlanadi).

## 2. Serverga ulanish va tayyorlash

```bash
ssh root@SERVER_IP
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx unzip
```

Xavfsizlik uchun alohida foydalanuvchi yarating (root ostida doim ishlash
tavsiya etilmaydi):

```bash
adduser botuser
usermod -aG sudo botuser
su - botuser
```

## 3. Loyihani serverga yuklash

Zaxira nusxa sifatida zip fayl orqali (kompyuteringizdan):

```bash
# O'zingizning kompyuteringizda (Windows'da PowerShell yoki WSL):
scp telegram_taxi_delivery.zip botuser@SERVER_IP:/opt/

# Serverda:
sudo unzip /opt/telegram_taxi_delivery.zip -d /opt/
sudo chown -R botuser:botuser /opt/telegram_taxi_delivery
cd /opt/telegram_taxi_delivery
```

(Agar loyihani GitHub'da saqlasangiz, buning o'rniga `git clone` ishlatish
ham qulay — keyinchalik yangilanishlarni `git pull` bilan olib kelasiz.)

## 4. Python muhitini sozlash

```bash
cd /opt/telegram_taxi_delivery
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. `.env` faylini production qiymatlari bilan to'ldirish

```bash
cp .env.example .env
nano .env
```

**Muhim:** production uchun:
- Haqiqiy `CLIENT_BOT_TOKEN` va `DRIVER_BOT_TOKEN`
- `ADMIN_PANEL_PASSWORD` — kuchli, uzun parol
- `ADMIN_PANEL_SECRET_KEY` — tasodifiy uzun satr. Generatsiya qilish uchun:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- `PAYME_MERCHANT_ID`, `PAYME_SECRET_KEY`, `CLICK_MERCHANT_ID`,
  `CLICK_SERVICE_ID`, `CLICK_SECRET_KEY` — agar onlayn to'lovni yoqmoqchi
  bo'lsangiz (8-bo'limga qarang). Bo'sh qoldirsangiz, mijozlarga faqat naqd
  to'lov ko'rsatiladi — hech narsa buzilmaydi.

## 6. Botlarni va to'lov serverini systemd xizmati sifatida ishga tushirish

`deploy/telegram-bot.service`, `deploy/admin-panel.service` va
`deploy/payments-server.service` fayllari tayyor — faqat ko'chirib, yoqish
kerak:

```bash
sudo cp deploy/telegram-bot.service /etc/systemd/system/
sudo cp deploy/admin-panel.service /etc/systemd/system/
sudo cp deploy/payments-server.service /etc/systemd/system/
sudo cp deploy/api-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-bot
sudo systemctl enable --now admin-panel
sudo systemctl enable --now payments-server
sudo systemctl enable --now api-server
```

Ishlab turganini tekshirish:

```bash
sudo systemctl status telegram-bot
sudo systemctl status admin-panel
sudo systemctl status payments-server
```

Loglarni ko'rish:

```bash
journalctl -u telegram-bot -f
journalctl -u admin-panel -f
journalctl -u payments-server -f
```

`enable` buyrug'i tufayli, server qayta yuklansa ham botlar avtomatik ishga
tushadi. `Restart=always` tufayli, dastur xato bilan to'xtab qolsa, 5 soniyadan
keyin avtomatik qayta ishga tushadi.

## 7. Admin panelni domen orqali ochish (ixtiyoriy, lekin tavsiya etiladi)

Agar domeningiz bo'lsa (masalan `admin.sizningdomeningiz.uz`), uni serverning
IP manziliga yo'naltiring (A yozuvi), so'ng:

```bash
sudo cp deploy/nginx-admin.conf /etc/nginx/sites-available/admin-panel
sudo nano /etc/nginx/sites-available/admin-panel  # domenni to'g'irlang
sudo ln -s /etc/nginx/sites-available/admin-panel /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL sertifikat (bepul, Let's Encrypt):
sudo certbot --nginx -d admin.sizningdomeningiz.uz
```

Shundan keyin `https://admin.sizningdomeningiz.uz` orqali admin panelga
xavfsiz kirasiz. Certbot sertifikatni avtomatik yangilab turadi.

Domen bo'lmasa, admin panelni faqat SSH tunnel orqali xavfsiz ochish mumkin:

```bash
# O'z kompyuteringizda:
ssh -L 8000:127.0.0.1:8000 botuser@SERVER_IP
# Keyin brauzerda: http://localhost:8000
```

## 8. To'lov webhook serverini ochish (Payme/Click uchun SHART)

Admin paneldan farqli o'laroq, to'lov serveri **albatta Internetga ochiq va
HTTPS orqali** ishlashi kerak — aks holda Payme/Click sizning serveringizga
murojaat qila olmaydi. Domeningizni (masalan
`pay.sizningdomeningiz.uz`) serverning IP manziliga yo'naltiring, so'ng:

```bash
sudo cp deploy/nginx-payments.conf /etc/nginx/sites-available/payments
sudo nano /etc/nginx/sites-available/payments  # domenni to'g'irlang
sudo ln -s /etc/nginx/sites-available/payments /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d pay.sizningdomeningiz.uz
```

Shundan so'ng Payme va Click Merchant kabinetlarida webhook manzillarini
shunga o'rnating:

- Payme: `https://pay.sizningdomeningiz.uz/payme`
- Click: `https://pay.sizningdomeningiz.uz/click/prepare` va
  `https://pay.sizningdomeningiz.uz/click/complete`

Xuddi shu tarzda, agar mobil ilovani (Flutter) ishlatsangiz, **API serverini
ham** ochiq domen orqali chiqarish kerak — `deploy/nginx-api.conf` shu uchun
tayyor (masalan `api.sizningdomeningiz.uz`, keyin
`certbot --nginx -d api.sizningdomeningiz.uz`). Mobil ilova ichida shu
manzilni ko'rsatasiz (`mobile_app/lib/services/api_client.dart` da).

**Eslatma:** Payme va Click bilan haqiqiy shartnoma tuzish (merchant ID va
maxfiy kalitlarni olish) alohida, kodlashdan tashqari jarayon — ular orqali
ishlash uchun biznesingizni ularning kabinetida ro'yxatdan o'tkazishingiz va
odatda yuridik shaxs sifatida shartnoma imzolashingiz kerak bo'ladi.
Ro'yxatdan o'tgach, ular sizga test (sandbox) muhitida tekshirish imkonini
beradi — ishga tushirishdan oldin albatta shu orqali sinab ko'ring.

## 9. Zaxira nusxa (backup)

```bash
chmod +x deploy/backup.sh
crontab -e
```

Ochilgan faylga qo'shing (har kuni soat 03:00 da zaxira oladi):

```
0 3 * * * /opt/telegram_taxi_delivery/deploy/backup.sh >> /var/log/taxi-backup.log 2>&1
```

## 10. Yangilanish qanday joylashtiriladi

Kodga o'zgarish kiritganingizda:

```bash
cd /opt/telegram_taxi_delivery
# Yangi fayllarni yuklang yoki git pull qiling
source venv/bin/activate
pip install -r requirements.txt  # agar yangi kutubxona qo'shilgan bo'lsa
sudo systemctl restart telegram-bot
sudo systemctl restart admin-panel
sudo systemctl restart payments-server
```

## 11. Xavfsizlik nazorat ro'yxati

- [ ] `.env` faylidagi barcha standart qiymatlar (`changeme` va h.k.) almashtirilgan
- [ ] Firewall yoqilgan va faqat kerakli portlar ochiq:
  ```bash
  sudo ufw allow OpenSSH
  sudo ufw allow 'Nginx Full'
  sudo ufw enable
  ```
- [ ] Admin panel to'g'ridan-to'g'ri internetga ochiq emas (faqat
  `127.0.0.1:8000` da, nginx orqali yoki SSH tunnel orqali kirish)
- [ ] To'lov serveri HTTPS orqali ochiq va Payme/Click kabinetida webhook
  manzillari to'g'ri sozlangan
- [ ] Bot tokenlari va to'lov maxfiy kalitlari hech qayerda (chat, kod,
  GitHub'ning ochiq repo'sida) oshkor qilinmagan
- [ ] Zaxira nusxa muntazam olinib turibdi
