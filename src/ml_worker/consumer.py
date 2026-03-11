import asyncio
import json
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.shared.config import settings
from src.shared.database import engine, Base, async_session
from src.shared.models import ClientChurnLog
from src.ml_worker.predictor import predictor
from src.shared.kafka_admin import create_topics

async def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных инициализирована.")


async def consume():
    """Главный процесс: читает из Kafka, считает ML скор, пишет в БД и Kafka"""
    
    await init_db()

    # ── НОВОЕ: загружаем модель ДО старта консьюмера ──────────────
    predictor.load()  # fail fast — если модели нет, падаем сразу
    # ──────────────────────────────────────────────────────────────
    await create_topics()

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_RAW,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="churn_prediction_group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    for attempt in range(1, 11):
        try:
            await consumer.start()
            await producer.start()
            print(f"🎧 ml_worker подключён к Kafka")
            break
        except Exception as e:
            wait = 2 * (2 ** (attempt - 1))
            print(f"⚠️  Попытка {attempt}/10 — {e}. Ждём {wait:.0f}s...")
            if attempt == 10:
                raise
            await asyncio.sleep(wait)

    try:
        async for msg in consumer:
            data = msg.value
            user_id = data["user_id"]
            print(f"\n📥 Получено сообщение: user_id={user_id}")

            try:
                # ── ML инференс ───────────────────────────────────────────
                churn_probability = predictor.predict(data)
                print(f"🧠 CatBoost: churn_probability={churn_probability}")
                # ─────────────────────────────────────────────────────────

                # ── Сохраняем в PostgreSQL ────────────────────────────────
                async with async_session() as session:
                    new_log = ClientChurnLog(
                        user_id=user_id,
                        credit_score=data["credit_score"],
                        geography=data["geography"],
                        gender=data["gender"],
                        age=data["age"],
                        tenure=data["tenure"],
                        balance=data["balance"],
                        num_of_products=data["num_of_products"],
                        has_cr_card=data["has_cr_card"],
                        is_active_member=data["is_active_member"],
                        estimated_salary=data["estimated_salary"],
                        complain=data["complain"],
                        satisfaction_score=data["satisfaction_score"],
                        subscription_type=data["subscription_type"],
                        points_earned=data["points_earned"],
                        timestamp=datetime.fromisoformat(
                            data["timestamp"]
                        ).replace(tzinfo=None),
                        churn_probability=churn_probability,
                    )
                    session.add(new_log)
                    await session.commit()
                print(f"💾 Сохранено в PostgreSQL")
                # ─────────────────────────────────────────────────────────

                # ── Публикуем результат в scored-events ───────────────────
                scored_event = {
                    "user_id": user_id,
                    "churn_probability": churn_probability,
                    "timestamp": data["timestamp"],
                }
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_SCORED,
                    value=scored_event
                )
                print(f"🚀 Результат отправлен в '{settings.KAFKA_TOPIC_SCORED}'")
                # ─────────────────────────────────────────────────────────

            except KeyError as e:
                # Битое сообщение — отсутствует обязательное поле
                print(f"⚠️  KeyError для user_id={user_id}: {e} — пропускаем")

            except Exception as e:
                # Любая другая ошибка (математика, БД и т.д.)
                print(f"❌ Ошибка обработки user_id={user_id}: {e}")

            print("-" * 50)

    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(consume())
