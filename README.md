# 🏦 Bank Customer Churn EDA System (HighLoad ML Architecture)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)
![Kafka](https://img.shields.io/badge/Apache_Kafka-Event_Driven-231F20?logo=apachekafka)
![CatBoost](https://img.shields.io/badge/CatBoost-ML-yellow)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

## 📌 Описание проекта
HighLoad-система для предсказания оттока клиентов банка (Churn Rate) в режиме Near-Real-Time. 
Проект реализует микросервисную **Event-Driven Architecture (EDA)** для обработки непрерывного потока транзакционных и поведенческих данных клиентов. 
Система защищена от дублирования сообщений (Idempotency) с помощью Redis и реализует паттерн DLQ (Dead Letter Queue) для обработки невалидных данных (Poison Pills).

**ML задача:** Бинарная классификация оттока на основе [Kaggle Bank Customer Churn Dataset].

## 🏗  Инфра
```mermaid
flowchart TD
    %% ── Клиент ──────────────────────────────────────────
    CLIENT(["👤 Клиент / Simulator"])

    %% ── API Gateway ──────────────────────────────────────
    subgraph GW["🌐 API Gateway (FastAPI)"]
        VALIDATE["✅ Валидация\nPydantic\nClientChurnEvent"]
        PRODUCE["📤 AIOKafkaProducer\nsend_and_wait()"]
        GET_RESULT["🔍 GET /result/user_id\nSELECT last record"]
        RISK["🎯 Интерпретация риска\n🔴≥0.7 / 🟡≥0.4 / 🟢<0.4"]
    end

    %% ── Kafka ────────────────────────────────────────────
    subgraph KAFKA["📨 Kafka Broker (3 партиции)"]
        RAW[("📥 churn-raw-events\n3 partitions")]
        SCORED[("📤 scored-events\n3 partitions")]
    end

    %% ── ML Worker ────────────────────────────────────────
    subgraph WORKER["⚙️ ML Worker"]
        CONSUME_ML["🎧 AIOKafkaConsumer\nml_worker_group"]
        PREDICT["🧠 CatBoost\nchurn_probability"]
        SAVE_PG["💾 INSERT INTO\nclient_churn_logs"]
        PUBLISH["🚀 Публикует\nв scored-events"]
    end

    %% ── Sink Worker ──────────────────────────────────────
    subgraph SINK["🪣 Sink Worker"]
        CONSUME_SINK["🎧 AIOKafkaConsumer\nsink_worker_group"]
        DECODE["🔍 UTF-8 decode\n+ JSON parse\n+ validate fields"]
        ROUTE{"prob ≥ 0.7?"}
        HIGH["🔴 High-risk\nhandle_high_risk()"]
        LOW["🟢 Low-risk\nпропускаем"]
        POISON["☠️ Poison\nDLQ handler"]
    end

    %% ── Хранилища ────────────────────────────────────────
    subgraph DB["🗄️ PostgreSQL"]
        LOGS[("📋 client_churn_logs")]
    end

    subgraph MONGO["🍃 MongoDB bank_churn"]
        MDB_HIGH[("🔴 high_risk\nколлекция")]
        MDB_POISON[("☠️ poison\nколлекция DLQ")]
    end

    subgraph FUTURE["🔮 В разработке"]
        DASH["streamlit_app\n⬜ пустой"]
    end

    %% ── Поток данных ─────────────────────────────────────
    CLIENT -->|"POST /events/"| VALIDATE
    VALIDATE -->|"422 ошибка"| CLIENT
    VALIDATE -->|"данные валидны"| PRODUCE
    PRODUCE -->|"пишет событие"| RAW
    PRODUCE -->|"accepted"| CLIENT

    RAW -->|"polling\nml_worker_group"| CONSUME_ML
    CONSUME_ML --> PREDICT
    PREDICT --> SAVE_PG
    SAVE_PG --> LOGS
    PREDICT --> PUBLISH
    PUBLISH --> SCORED

    SCORED -->|"polling\nsink_worker_group"| CONSUME_SINK
    CONSUME_SINK --> DECODE
    DECODE -->|"битый JSON\nили нет полей"| POISON
    DECODE -->|"валидное сообщение"| ROUTE
    ROUTE -->|"да"| HIGH
    ROUTE -->|"нет"| LOW
    HIGH --> MDB_HIGH
    POISON --> MDB_POISON

    CLIENT -->|"GET /result/user_id"| GET_RESULT
    GET_RESULT -->|"SELECT WHERE user_id\nORDER BY timestamp DESC"| LOGS
    LOGS -->|"churn_probability"| GET_RESULT
    GET_RESULT --> RISK
    RISK -->|"JSON ответ"| CLIENT

    DASH -->|"читает аналитику"| LOGS
    DASH -->|"читает high-risk"| MDB_HIGH

    %% ── Стили ────────────────────────────────────────────
    style CLIENT fill:#4A90D9,color:#fff
    style VALIDATE fill:#27AE60,color:#fff
    style PRODUCE fill:#27AE60,color:#fff
    style GET_RESULT fill:#27AE60,color:#fff
    style RISK fill:#27AE60,color:#fff
    style RAW fill:#E67E22,color:#fff
    style SCORED fill:#E67E22,color:#fff
    style CONSUME_ML fill:#8E44AD,color:#fff
    style PREDICT fill:#8E44AD,color:#fff
    style SAVE_PG fill:#8E44AD,color:#fff
    style PUBLISH fill:#8E44AD,color:#fff
    style CONSUME_SINK fill:#2980B9,color:#fff
    style DECODE fill:#2980B9,color:#fff
    style ROUTE fill:#2980B9,color:#fff
    style HIGH fill:#E74C3C,color:#fff
    style LOW fill:#27AE60,color:#fff
    style POISON fill:#2C3E50,color:#fff
    style LOGS fill:#2ECC71,color:#fff
    style MDB_HIGH fill:#E74C3C,color:#fff
    style MDB_POISON fill:#2C3E50,color:#fff
    style DASH fill:#95A5A6,color:#fff
```

---

## 🔄 Поток данных

| Шаг | Компонент | Действие |
|-----|-----------|----------|
| 1 | **Клиент / Simulator** | `POST /events/` — отправляет данные клиента банка |
| 2 | **API Gateway** | Валидация через Pydantic. При ошибке → `422` |
| 3 | **Kafka Producer** | Публикует событие в `churn-raw-events`. Возвращает `accepted` |
| 4 | **ML Worker** | Читает из `churn-raw-events` (`ml_worker_group`) |
| 5 | **CatBoost** | Вычисляет `churn_probability` (0..1) |
| 6 | **PostgreSQL** | `INSERT` результата в `client_churn_logs` |
| 7 | **Kafka Producer** | Публикует результат в `scored-events` |
| 8 | **Sink Worker** | Читает из `scored-events` (`sink_worker_group`) |
| 9 | **Sink Worker** | UTF-8 → JSON → валидация полей. Битые → DLQ (`poison`) |
| 10 | **MongoDB** | `prob ≥ 0.7` → коллекция `high_risk`. Иначе — пропуск |
| 11 | **Клиент** | `GET /result/{user_id}` → получает `churn_probability` + 🔴🟡🟢 |

---

## 📁 Структура проекта

```
src/
├── api_gateway/                 # 🌐 HTTP точка входа
│   ├── main.py                  # FastAPI: /events/, /result/{user_id}, /
│   └── kafka_producer.py        # Синглтон AIOKafkaProducer (start/stop/get)
│
├── ml_worker/                   # ⚙️ Предсказание оттока
│   ├── consumer.py              # Consumer: churn-raw-events → predict → scored-events
│   └── predictor.py             # Загрузка CatBoost, возвращает churn_probability
│
├── sink_worker/                 # 🪣 Фильтрация и сохранение в MongoDB
│   ├── consumer.py              # Consumer: scored-events → high_risk / poison DLQ
│   └── mongo_client.py          # Синглтон MongoDB (connect/close, high_risk, poison)
│
├── simulator/                   # 🤖 Генератор тестовых данных
│   └── main.py                  # Генерирует N клиентов → POST /events/ (httpx)
│
├── shared/                      # 🔧 Общий код для всех сервисов
│   ├── config.py                # Settings (Pydantic BaseSettings) — читает .env
│   ├── database.py              # Async SQLAlchemy engine + get_session() для DI
│   ├── kafka_admin.py           # Создание топиков при старте, retry с backoff
│   ├── models.py                # ORM-модель ClientChurnLog (PostgreSQL)
│   ├── schemas.py               # Pydantic-схема ClientChurnEvent (валидация POST)
│   └── __init__.py
│
└── streamlit_app/               # 🔮 Дашборд (в разработке)
```

### Зависимости между модулями

```
simulator
    └──► api_gateway          (HTTP POST /events/)

api_gateway
    ├──► shared.schemas       (валидация входящих данных)
    ├──► shared.database      (чтение результатов GET /result)
    ├──► shared.models        (ORM ClientChurnLog)
    └──► kafka_producer       (отправка событий в Kafka)

ml_worker
    ├──► shared.config
    ├──► shared.database
    ├──► shared.models
    ├──► shared.kafka_admin
    └──► predictor            (CatBoost inference)

sink_worker
    ├──► shared.config
    ├──► shared.kafka_admin
    └──► mongo_client         (MongoDB high_risk + poison DLQ)
```

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-username/bank-churn-eda-system.git
cd bank-churn-eda-system
```

### 2. Создать `.env`

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_RAW=churn-raw-events
KAFKA_TOPIC_SCORED=scored-events

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bank_churn
MODEL_PATH=models/churn_model.cbm

MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=bank_churn
```

### 3. Запустить инфраструктуру

```bash
docker-compose up -d
```

### 4. Запустить сервисы

```bash
# API Gateway
uvicorn src.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload

# ML Worker
python -m src.ml_worker.consumer

# Sink Worker
python -m src.sink_worker.consumer

# Simulator (опционально)
python -m src.simulator.main
```

---

## 📡 API

### `POST /events/`
Принимает данные клиента банка, отправляет в Kafka.

```json
{
  "user_id": "user_1234",
  "credit_score": 650,
  "geography": "France",
  "gender": "Male",
  "age": 35,
  "tenure": 5,
  "balance": 125000.00,
  "num_of_products": 2,
  "has_cr_card": true,
  "is_active_member": true,
  "estimated_salary": 75000.00,
  "complain": false,
  "satisfaction_score": 4,
  "subscription_type": "GOLD",
  "points_earned": 450,
  "timestamp": "2024-01-15T10:30:00"
}
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Транзакция отправлена в Kafka",
  "topic": "churn-raw-events"
}
```

---

### `GET /result/{user_id}`
Возвращает последний результат предсказания для клиента.

**Ответ:**
```json
{
  "user_id": "user_1234",
  "churn_probability": 0.7823,
  "risk_level": "🔴 Высокий",
  "timestamp": "2024-01-15T10:30:05"
}
```

| `churn_probability` | `risk_level` |
|---------------------|--------------|
| ≥ 0.7 | 🔴 Высокий |
| ≥ 0.4 | 🟡 Средний |
| < 0.4 | 🟢 Низкий |

---

### `GET /`
Healthcheck.

```json
{ "status": "ok", "message": "Bank Churn API is running!" }
```

---

## ⚙️ Конфигурация

| Переменная | Описание | Пример |
|------------|----------|--------|
| `KAFKA_BOOTSTRAP_SERVERS` | Адрес Kafka брокера | `localhost:9092` |
| `KAFKA_TOPIC_RAW` | Топик сырых событий | `churn-raw-events` |
| `KAFKA_TOPIC_SCORED` | Топик результатов | `scored-events` |
| `DATABASE_URL` | PostgreSQL DSN | `postgresql+asyncpg://...` |
| `MODEL_PATH` | Путь к модели CatBoost | `models/churn_model.cbm` |
| `MONGODB_URI` | MongoDB DSN | `mongodb://localhost:27017` |
| `MONGODB_DB` | Название БД MongoDB | `bank_churn` |

---

## 🔮 В разработке

- [ ] `streamlit_app` — дашборд аналитики (PostgreSQL + MongoDB)
- [ ] Метрики Prometheus + Grafana
- [ ] Docker Compose для всех сервисов
- [ ] Production-конфигурация Kafka (replication factor = 3)
