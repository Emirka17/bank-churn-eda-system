import asyncio
import json
from datetime import datetime
from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.db.database import engine, Base, async_session
from app.db.models import TransactionRecord

async def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных инициализирована.")

async def consume():
    """Главный процесс слушателя: читает из Kafka, пишет в PostgreSQL"""
    await init_db()

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_RAW,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="churn_prediction_group", # Consumer Group - основа масштабирования Kafka
        value_deserializer=lambda x: json.loads(x.decode("utf-8")) # Расшифровываем JSON обратно в словарь
    )

    await consumer.start()
    print(f"🎧 Consumer запущен! Слушаем топик: {settings.KAFKA_TOPIC_RAW}...")

    try:
        # Это бесконечный цикл. Воркер будет "спать" и ждать, пока API не пришлет данные
        async for msg in consumer:
            data = msg.value
            print(f"📥 Получено сообщение из Kafka: {data}")
            
            # 1. (В будущем тут будет код нейросети: probability = model.predict(data))
            mock_probability = 0.5 # Пока просто "заглушка"
            
            # 2. Сохраняем в PostgreSQL
            async with async_session() as session:
                new_transaction = TransactionRecord(
                    user_id=data["user_id"],
                    amount=data["amount"],
                    timestamp=datetime.fromisoformat(data["timestamp"]).replace(tzinfo=None),
                    churn_probability=mock_probability
                )
                session.add(new_transaction)
                await session.commit()
                
            print(f"💾 Данные пользователя {data['user_id']} сохранены в базу!")
            print("-" * 30)
            
    finally:
        await consumer.stop()

if __name__ == "__main__":
    # Запускаем асинхронного слушателя
    asyncio.run(consume())
