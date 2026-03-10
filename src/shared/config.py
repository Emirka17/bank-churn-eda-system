from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bank Churn API Gateway"
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_RAW: str
    KAFKA_TOPIC_SCORED: str = "scored-events"
    
    DATABASE_URL: str
    MODEL_PATH: str = "models/churn_model.cbm"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Создаем объект настроек, который будем импортировать в других файлах
settings = Settings()
