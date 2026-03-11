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


## 🏗 Архитектура системы (Не актуально)

Ниже представлена C4 (Component) диаграмма развертывания проекта:

```mermaid
graph TD
    %% Узлы (Сущности)
    Sim[("⚙️ Simulator (Mock Bank App)")]
    API["🌐 FastAPI (API Gateway)"]
    Redis[("🗄️ Redis (Cache & Locks)")]
    Kafka{"🔀 Apache Kafka (Broker)"}
    ML_Worker["🧠 ML Worker (CatBoost)"]
    Mongo[("🍃 MongoDB (Audit Logs)")]
    PG_Meta[("🐘 Postgres (Model Catalog)")]
    PG_Data[("🐘 Postgres (Business Data)")]
    Sink["📥 Sink Worker (DB Loader)"]
    Streamlit["📊 Streamlit (Dashboard)"]

    %% Связи
    Sim -- "1. POST JSON" --> API
    API -- "2. Check Dedupe" --> Redis
    API -- "3. Publish Event" --> Kafka
    Kafka -- "4. Consume raw-events" --> ML_Worker
    ML_Worker -- "5. Get Model" --> PG_Meta
    ML_Worker -- "6. Audit Log" --> Mongo
    ML_Worker -- "7. Publish scored-events" --> Kafka
    Kafka -- "8. Consume scored-events" --> Sink
    Sink -- "9. Upsert State" --> PG_Data
    Streamlit -- "10. Read Data" --> PG_Data
```

## 🏗 Диаграмма процесса (Не актуально)

Это технический аналог BPMN, который пошагово описывает жизнь одного конкретного запроса во времени. Именно по этой схеме мы будем писать логику.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Bank System (Simulator)
    participant API as FastAPI Gateway
    participant Redis as Redis Cache
    participant Kafka as Kafka Broker
    participant ML as ML Worker
    participant Mongo as MongoDB
    participant PG as PostgreSQL

    Client->>API: POST /api/v1/scoring (client_id: 123, ...)
    
    rect rgb(240, 240, 240)
        Note over API, Redis: Фаза валидации и дедупликации
        API->>Redis: SETNX lock:event_123 
        alt Если ключ уже есть (Дубль)
            Redis-->>API: False
            API-->>Client: 409 Conflict (Duplicate)
        else Если новый запрос
            Redis-->>API: True
            API->>Kafka: Произвести в топик [raw-client-events]
            API-->>Client: 202 Accepted (In queue)
        end
    end

    rect rgb(230, 245, 255)
        Note over Kafka, Mongo: Фаза ML Инференса (Асинхронно)
        Kafka-->>ML: Чтение батча (poll)
        ML->>PG: SELECT * FROM models WHERE status='active' (Кэшируется локально)
        PG-->>ML: model_v2.cbm
        ML->>ML: Выполнение CatBoost (predict_proba)
        ML->>Mongo: Вставить аудит-лог (сырой JSON, фичи, время, prediction score)
        ML->>Kafka: Произвести в топик [scored-client-events]
    end

    rect rgb(230, 255, 230)
        Note over Kafka, PG: Фаза сохранения статуса (Sink)
        participant Sink as Sink Worker
        Kafka-->>Sink: Чтение батча скорринга
        Sink->>PG: INSERT ON CONFLICT UPDATE (client_id, churn_prob, updated_at)
    end
```
