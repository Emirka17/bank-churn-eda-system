from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bank Churn API Gateway"
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_RAW: str
    
    # ВОТ ЭТО НОВАЯ СТРОЧКА:
    DATABASE_URL: str
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Создаем объект настроек, который будем импортировать в других файлах
settings = Settings()
