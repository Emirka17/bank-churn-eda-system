import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.models.schemas import ClientChurnEvent
from app.kafka_producer import start_producer, stop_producer, get_producer

# Lifespan - это новый механизм FastAPI для управления запуском/остановкой базы и брокеров
@asynccontextmanager
async def lifespan(app: FastAPI):
    # То, что до yield - выполняется при включении сервера
    await start_producer()
    yield
    # То, что после yield - выполняется при выключении
    await stop_producer()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Bank Churn API is running!"}

@app.post("/events/")
async def receive_event(event: ClientChurnEvent, kafka: AIOKafkaProducer = Depends(get_producer)):
    """
    Принимаем транзакцию, валидируем и отправляем в очередь Kafka
    """
    event_dict = event.model_dump() # Превращаем Pydantic объект в обычный словарь
    event_dict['timestamp'] = event_dict['timestamp'].isoformat() # Превращаем время в строку, чтобы JSON смог это съесть
    
    # Отправляем в нужный топик
    await kafka.send_and_wait(settings.KAFKA_TOPIC_RAW, event_dict)
    
    return {
        "status": "success",
        "message": "Транзакция отправлена в Kafka",
        "topic": settings.KAFKA_TOPIC_RAW,
        "data": event_dict
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
