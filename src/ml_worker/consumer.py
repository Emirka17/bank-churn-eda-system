import asyncio
import json
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import settings
from app.db.database import engine, Base, async_session
# ВАЖНО: Мы изменили импорт модели на новую таблицу
from app.db.models import ClientChurnLog 
# Импортируем нашу новую заглушку для ML-модели
from app.ml.predictor import predictor 

async def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных инициализирована.")

async def consume():
    """Главный процесс слушателя: читает из Kafka, пишет в PostgreSQL и отправляет результат дальше"""
    await init_db()

    # 1. Настраиваем слушателя (Consumer)
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_RAW,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="churn_prediction_group", 
        value_deserializer=lambda x: json.loads(x.decode("utf-8")) 
    )

    # 2. НОВОЕ: Настраиваем отправителя (Producer)
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    await consumer.start()
    await producer.start() # Запускаем продюсер
    print(f"🎧 Consumer запущен! Слушаем топик: {settings.KAFKA_TOPIC_RAW}...")
    print(f"📤 Producer готов к отправке в топик: scored-events")

    try:
        async for msg in consumer:
            data = msg.value
            print(f"📥 Получено сообщение из Kafka: {data['user_id']}")
            
            # НОВОЕ: Вызываем заглушку ML-модели 
            churn_probability = predictor.predict(data) 
            
            # Сохраняем в PostgreSQL (теперь с новыми полями Датасета)
            async with async_session() as session:
                new_log = ClientChurnLog(
                    user_id=data["user_id"],
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
                    timestamp=datetime.fromisoformat(data["timestamp"]).replace(tzinfo=None),
                    churn_probability=churn_probability
                )
                session.add(new_log)
                await session.commit()
                
            print(f"💾 Данные пользователя {data['user_id']} сохранены в базу (Шанс оттока: {churn_probability})!")
            
            # НОВОЕ: Отправляем результат скоринга дальше в Kafka
            scored_event = {
                "user_id": data["user_id"],
                "churn_probability": churn_probability,
                "timestamp": data["timestamp"]
            }
            # Отправляем и ждем подтверждения от брокера Kafka
            await producer.send_and_wait("scored-events", value=scored_event)
            print(f"🚀 Результат улетел в топик 'scored-events': {scored_event}")
            print("-" * 30)
            
    finally:
        await consumer.stop()
        await producer.stop() # Не забываем закрыть соединение продюсера

if __name__ == "__main__":
    asyncio.run(consume())
