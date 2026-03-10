from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bank Churn API Gateway"
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_RAW: str
    KAFKA_TOPIC_SCORED: str = "scored-events"

    DATABASE_URL: str
    MODEL_PATH: str = str(Path("models") / "churn_model.cbm")

    # Убираем localhost — поля обязательные, без дефолта
    MONGODB_URI: str
    MONGODB_DB: str = "bank_churn"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
