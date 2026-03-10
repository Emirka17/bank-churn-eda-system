import json
from aiokafka import AIOKafkaProducer
from src.shared.config import settings

# Глобальная переменная для хранения запущенного продюсера
producer: AIOKafkaProducer = None

async def start_producer():
    """Эта функция запустится вместе со стартом нашего API"""
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        # Kafka принимает только байты, поэтому мы сериализуем словари в JSON, а затем кодируем в UTF-8
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    await producer.start()
    print("✅ Kafka Producer успешно подключен к брокеру!")

async def stop_producer():
    """Эта функция корректно отключит нас от Kafka при остановке сервера"""
    if producer:
        await producer.stop()
        print("🛑 Kafka Producer остановлен.")

async def get_producer() -> AIOKafkaProducer:
    """Функция, которая будет отдавать продюсера нашим эндпоинтам"""
    return producer
