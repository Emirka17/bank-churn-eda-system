from motor.motor_asyncio import AsyncIOMotorClient
from src.shared.config import settings

class MongoManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.high_risk = None      # коллекция high_risk_clients
        self.poison = None         # коллекция poison_messages

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB]
        self.high_risk = self.db["high_risk_clients"]
        self.poison   = self.db["poison_messages"]
        print("✅ MongoDB подключена")

    async def close(self):
        if self.client:
            self.client.close()
            print("🔌 MongoDB отключена")

mongo = MongoManager()
