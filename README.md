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
