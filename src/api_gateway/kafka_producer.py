import json
import asyncio
from aiokafka import AIOKafkaProducer
from src.shared.config import settings
from src.shared.kafka_admin import create_topics

producer: AIOKafkaProducer = None

async def start_producer(retries: int = 10, delay: float = 2.0):
    await create_topics()
    
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    for attempt in range(1, retries + 1):
        try:
            await producer.start()
            print("✅ Kafka Producer подключен!")
            return
        except Exception as e:
            wait = delay * (2 ** (attempt - 1))  # 2s, 4s, 8s...
            print(f"⚠️  Попытка {attempt}/{retries} — Kafka недоступна: {e}. Ждём {wait:.0f}s...")
            if attempt == retries:
                raise RuntimeError(f"Kafka недоступна после {retries} попыток") from e
            await asyncio.sleep(wait)

async def stop_producer():
    if producer:
        await producer.stop()
        print("🛑 Kafka Producer остановлен.")

async def get_producer() -> AIOKafkaProducer:
    return producer
