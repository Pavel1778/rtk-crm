FROM python:3.11-slim

# Рабочая директория — корень, чтобы пакет `app` лежал в /app
WORKDIR /

# Системные зависимости
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirror.yandex.ru|g; s|security.debian.org|mirror.yandex.ru|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|deb.debian.org|mirror.yandex.ru|g; s|security.debian.org|mirror.yandex.ru|g' /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl fonts-dejavu-core; \
    rm -rf /var/lib/apt/lists/*

# Корневой сертификат НУЦ Минцифры: токен GigaChat выдаётся с сертификатом
# этого УЦ, которого нет в стандартном наборе доверенных корней образа.
# Кладём в системный набор (для любых клиентов) и в /certs (путь по умолчанию
# в backend/services/gigachat.py).
COPY certs/russian_trusted_root_ca.pem /usr/local/share/ca-certificates/russian_trusted_root_ca.crt
RUN update-ca-certificates && mkdir -p /certs \
    && cp /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
          /certs/russian_trusted_root_ca.pem

# Python-зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем всё содержимое backend/ в /app/
COPY . /app/

ENV PYTHONPATH=/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]