FROM python:3.11-slim

# Рабочая директория — корень, чтобы пакет `app` лежал в /app
WORKDIR /

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем всё содержимое backend/ в /app/
COPY . /app/

ENV PYTHONPATH=/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]