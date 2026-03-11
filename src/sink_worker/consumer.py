import asyncio
import json
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer

from src.shared.config import settings
from src.sink_worker.mongo_client import mongo
from src.shared.kafka_admin import create_topics

# Порог высокого риска
HIGH_RISK_THRESHOLD = 0.7


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def handle_high_risk(data: dict):
    """Валидное сообщение с высоким риском → пишем в MongoDB"""
    doc = {
        "user_id":           data["user_id"],
        "churn_probability": data["churn_probability"],
        "timestamp":         data["timestamp"],
        "received_at":       _now(),
    }
    await mongo.high_risk.insert_one(doc)
    print(f"🔴 High-risk сохранён в MongoDB: user_id={data['user_id']} "
          f"prob={data['churn_probability']:.3f}")


async def handle_poison(raw, error: str, topic: str, partition: int, offset: int):
    """Битое сообщение → пишем в MongoDB как poison message (DLQ)"""
    doc = {
        "raw_message": raw if isinstance(raw, str) else str(raw),
        "error":       error,
        "topic":       topic,
        "partition":   partition,
        "offset":      offset,
        "received_at": _now(),
    }
    await mongo.poison.insert_one(doc)
    print(f"☠️  Poison message сохранён: offset={offset} error={error}")


async def consume():
    
    await mongo.connect()
    await mongo.connect()

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_SCORED,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="sink_worker_group",
        # raw байты — НЕ десериализуем автоматически
        # чтобы поймать битый JSON до того как упадёт
        value_deserializer=None,
    )

    for attempt in range(1, 11):
        try:
            await consumer.start()
            print(f"🎧 sink_worker подключён к Kafka")
            break
        except Exception as e:
            wait = 2 * (2 ** (attempt - 1))
            print(f"⚠️  Попытка {attempt}/10 — {e}. Ждём {wait:.0f}s...")
            if attempt == 10:
                raise
            await asyncio.sleep(wait)

    try:
        async for msg in consumer:
            raw_bytes = msg.value
            topic     = msg.topic
            partition = msg.partition
            offset    = msg.offset

            # ── Шаг 1: пытаемся декодировать байты ───────────────────────
            try:
                raw_str = raw_bytes.decode("utf-8")
            except Exception as e:
                await handle_poison(
                    raw=raw_bytes,
                    error=f"UTF-8 decode error: {e}",
                    topic=topic, partition=partition, offset=offset,
                )
                continue

            # ── Шаг 2: пытаемся распарсить JSON ──────────────────────────
            try:
                data = json.loads(raw_str)
            except json.JSONDecodeError as e:
                await handle_poison(
                    raw=raw_str,
                    error=f"JSON parse error: {e}",
                    topic=topic, partition=partition, offset=offset,
                )
                continue

            # ── Шаг 3: проверяем обязательные поля ───────────────────────
            required_fields = {"user_id", "churn_probability", "timestamp"}
            missing = required_fields - data.keys()
            if missing:
                await handle_poison(
                    raw=raw_str,
                    error=f"Missing fields: {missing}",
                    topic=topic, partition=partition, offset=offset,
                )
                continue

            # ── Шаг 4: проверяем тип churn_probability ────────────────────
            try:
                prob = float(data["churn_probability"])
            except (ValueError, TypeError) as e:
                await handle_poison(
                    raw=raw_str,
                    error=f"Invalid churn_probability: {e}",
                    topic=topic, partition=partition, offset=offset,
                )
                continue

            # ── Шаг 5: роутинг по порогу ─────────────────────────────────
            if prob >= HIGH_RISK_THRESHOLD:
                await handle_high_risk(data)
            else:
                print(f"✅ Low-risk: user_id={data['user_id']} "
                      f"prob={prob:.3f} — пропускаем")

            print("-" * 50)

    finally:
        await consumer.stop()
        await mongo.close()


if __name__ == "__main__":
    asyncio.run(consume())
