FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Было: /app/src — неправильно
# Стало: /app — правильно, тогда from src.shared... работает
ENV PYTHONPATH=/app
