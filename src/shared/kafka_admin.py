# src/shared/kafka_admin.py

import asyncio
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from src.shared.config import settings


TOPICS = [
    NewTopic(
        name=settings.KAFKA_TOPIC_RAW,
        num_partitions=3,        # 3 партиции = 3 параллельных консьюмера
        replication_factor=1     # 1 для dev, 3 для production
    ),
    NewTopic(
        name=settings.KAFKA_TOPIC_SCORED,
        num_partitions=3,
        replication_factor=1
    ),
]


async def create_topics(retries: int = 10, delay: float = 2.0):
    """Создаём топики если их ещё нет. Вызывается при старте каждого сервиса."""
    for attempt in range(1, retries + 1):
        admin = AIOKafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )
        try:
            await admin.start()

            existing = await admin.list_topics()
            to_create = [t for t in TOPICS if t.name not in existing]

            if to_create:
                await admin.create_topics(to_create)
                for t in to_create:
                    print(f"✅ Топик создан: {t.name} "
                          f"(partitions={t.num_partitions})")
            else:
                print("✅ Все топики уже существуют")

            await admin.close()
            return

        except Exception as e:
            await admin.close()
            wait = delay * (2 ** (attempt - 1))
            print(f"⚠️  Попытка {attempt}/{retries} — Kafka недоступна: {e}. "
                  f"Ждём {wait:.0f}s...")
            if attempt == retries:
                raise RuntimeError(
                    f"Не удалось создать топики после {retries} попыток"
                ) from e
            await asyncio.sleep(wait)
