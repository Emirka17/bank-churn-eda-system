from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# ЭТО НОВАЯ СХЕМА
class ClientChurnEvent(BaseModel):
    user_id: str
    credit_score: int = Field(..., description="Кредитный рейтинг")
    geography: str = Field(..., description="Страна")
    gender: Literal["Male", "Female"] = Field(..., description="Пол")
    age: int = Field(..., description="Возраст")
    tenure: int = Field(..., description="Лет с банком")
    balance: float = Field(..., description="Баланс")
    num_of_products: int = Field(..., description="Количество продуктов")
    has_cr_card: bool = Field(..., description="Наличие кредитки")
    is_active_member: bool = Field(..., description="Активность")
    estimated_salary: float = Field(..., description="Ожидаемая зарплата")
    complain: bool = Field(..., description="Жалобы")
    satisfaction_score: int = Field(..., description="Оценка саппорта")
    subscription_type: Literal["DIAMOND", "GOLD", "SILVER", "PLATINUM"] = Field(..., description="Тип подписки")
    points_earned: int = Field(..., description="Заработанные баллы")
    timestamp: datetime
