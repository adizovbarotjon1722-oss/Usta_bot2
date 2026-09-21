FROM python:3.11-slim

# Ishchi katalog
WORKDIR /app

# Tizim paketlarini yangilash
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Talab qilinadigan Python paketlarni o'rnatish
COPY requirements.txt .
COPY webapp/requirements.txt ./webapp_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r webapp_requirements.txt

# Loyiha kodini ko'chirish
COPY . .

# Ma'lumotlar bazasi, zaxiralar va loglar uchun papkalar
RUN mkdir -p /app/backups /app/logs

# Web panel porti
EXPOSE 8000

# Standart buyruq - botni ishga tushirish
CMD ["python", "main.py"]
