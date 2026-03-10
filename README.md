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

## 🏗 Архитектура системы

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

## 🏗 Диаграмма процесса 

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

## 🏗  Инфра
```mermaid
flowchart TD
    %% ── Клиент ──────────────────────────────────────────
    CLIENT(["👤 Клиент"])

    %% ── API Gateway ──────────────────────────────────────
    subgraph GW["🌐 API Gateway (FastAPI)"]
        VALIDATE["✅ Валидация\nPydantic"]
        PRODUCE["📤 Kafka Producer"]
        GET_RESULT["🔍 GET /result/user_id"]
    end

    %% ── Kafka ────────────────────────────────────────────
    subgraph KAFKA["📨 Kafka Broker"]
        RAW[("📥 churn-raw-events")]
        SCORED[("📤 churn-scored-events")]
    end

    %% ── ML Worker ────────────────────────────────────────
    subgraph WORKER["⚙️ ML Worker"]
        CONSUME["🎧 Consumer\nчитает сообщение"]
        PREDICT["🧠 CatBoost\nchurn_probability"]
        SAVE_PG["💾 Сохранить\nв PostgreSQL"]
        PUBLISH["🚀 Публикует\nрезультат"]
    end

    %% ── Хранилища ────────────────────────────────────────
    subgraph DB["🗄️ PostgreSQL"]
        LOGS[("📋 client_churn_logs")]
        TXN[("💳 transactions")]
    end

    subgraph FUTURE["🔮 В разработке"]
        SINK["sink_worker\n⬜ пустой"]
        MONGO[("🍃 MongoDB\nсырые логи")]
        SIM["simulator\n⬜ пустой"]
        DASH["streamlit_app\n⬜ пустой"]
    end

    %% ── Поток данных ─────────────────────────────────────
    CLIENT -->|"POST /predict"| VALIDATE
    VALIDATE -->|"данные валидны"| PRODUCE
    VALIDATE -->|"422 ошибка"| CLIENT
    PRODUCE -->|"пишет событие"| RAW
    PRODUCE -->|"accepted"| CLIENT

    RAW -->|"polling"| CONSUME
    CONSUME --> PREDICT
    PREDICT --> SAVE_PG
    SAVE_PG --> LOGS
    PREDICT --> PUBLISH
    PUBLISH --> SCORED

    SCORED -->|"читает"| SINK
    SINK --> MONGO
    SIM -->|"генерирует\nтестовых клиентов"| VALIDATE
    DASH -->|"читает аналитику"| LOGS
    DASH -->|"читает сырые логи"| MONGO

    CLIENT -->|"GET /result/user_id"| GET_RESULT
    GET_RESULT -->|"SELECT WHERE user_id"| LOGS
    LOGS -->|"churn_probability"| GET_RESULT
    GET_RESULT -->|"JSON ответ"| CLIENT

    %% ── Стили ────────────────────────────────────────────
    style CLIENT fill:#4A90D9,color:#fff
    style VALIDATE fill:#27AE60,color:#fff
    style PRODUCE fill:#27AE60,color:#fff
    style GET_RESULT fill:#27AE60,color:#fff
    style RAW fill:#E67E22,color:#fff
    style SCORED fill:#E67E22,color:#fff
    style CONSUME fill:#8E44AD,color:#fff
    style PREDICT fill:#8E44AD,color:#fff
    style SAVE_PG fill:#8E44AD,color:#fff
    style PUBLISH fill:#8E44AD,color:#fff
    style LOGS fill:#2ECC71,color:#fff
    style TXN fill:#2ECC71,color:#fff
    style SINK fill:#95A5A6,color:#fff
    style MONGO fill:#95A5A6,color:#fff
    style SIM fill:#95A5A6,color:#fff
    style DASH fill:#95A5A6,color:#fffs
```
