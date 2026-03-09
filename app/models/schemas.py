from pydantic import BaseModel, Field
from datetime import datetime

class TransactionEvent(BaseModel):
    # Field(...) означает, что поле обязательное
    user_id: str = Field(..., description="Уникальный ID клиента")
    amount: float = Field(..., description="Сумма транзакции")
    # Если время не передали, подставим текущее сами
    timestamp: datetime = Field(default_factory=datetime.utcnow)
