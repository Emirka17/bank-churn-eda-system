from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from src.shared.database import Base

class ClientChurnLog(Base):
    __tablename__ = "client_churn_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    credit_score = Column(Integer)
    geography = Column(String)
    gender = Column(String)
    age = Column(Integer)
    tenure = Column(Integer)
    balance = Column(Float)
    num_of_products = Column(Integer)
    has_cr_card = Column(Boolean)
    is_active_member = Column(Boolean)
    estimated_salary = Column(Float)
    complain = Column(Boolean)
    satisfaction_score = Column(Integer)
    subscription_type = Column(String)
    points_earned = Column(Integer)
    
    timestamp = Column(DateTime)
    churn_probability = Column(Float) # Результат предсказания
