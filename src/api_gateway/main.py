import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from aiokafka import AIOKafkaProducer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import settings
from src.shared.schemas import ClientChurnEvent
from src.shared.database import get_session        # зависимость для сессии БД
from src.shared.models import ClientChurnLog       # модель таблицы
from src.api_gateway.kafka_producer import start_producer, stop_producer, get_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Bank Churn API is running!"}


@app.post("/events/")
async def receive_event(
    event: ClientChurnEvent,
    kafka: AIOKafkaProducer = Depends(get_producer)
):
    event_dict = event.model_dump()
    event_dict['timestamp'] = event_dict['timestamp'].isoformat()
    await kafka.send_and_wait(settings.KAFKA_TOPIC_RAW, event_dict)
    return {
        "status": "success",
        "message": "Транзакция отправлена в Kafka",
        "topic": settings.KAFKA_TOPIC_RAW,
        "data": event_dict
    }


@app.get("/result/{user_id}")
async def get_result(
    user_id: str,
    db: AsyncSession = Depends(get_session)
):
    # Ищем последний результат по user_id
    result = await db.execute(
        select(ClientChurnLog)
        .where(ClientChurnLog.user_id == user_id)
        .order_by(ClientChurnLog.timestamp.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=404, detail=f"Результат для {user_id} не найден")

    # Интерпретация риска
    if log.churn_probability >= 0.7:
        risk = "🔴 Высокий"
    elif log.churn_probability >= 0.4:
        risk = "🟡 Средний"
    else:
        risk = "🟢 Низкий"

    return {
        "user_id": log.user_id,
        "churn_probability": round(log.churn_probability, 4),
        "risk_level": risk,
        "timestamp": log.timestamp
    }


if __name__ == "__main__":
    uvicorn.run("src.api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
