import asyncio
import random
import httpx
from datetime import datetime


API_URL = "http://localhost:8000/events/"
NUM_CLIENTS = 20       # сколько клиентов сгенерировать
DELAY_SECONDS = 0.5    # пауза между запросами


def generate_client() -> dict:
    return {
        "user_id": f"user_{random.randint(1000, 9999)}",
        "credit_score": random.randint(300, 850),
        "geography": random.choice(["France", "Germany", "Spain"]),
        "gender": random.choice(["Male", "Female"]),
        "age": random.randint(18, 70),
        "tenure": random.randint(0, 10),
        "balance": round(random.uniform(0, 250000), 2),
        "num_of_products": random.randint(1, 4),
        "has_cr_card": random.choice([True, False]),
        "is_active_member": random.choice([True, False]),
        "estimated_salary": round(random.uniform(20000, 200000), 2),
        "complain": random.choice([True, False]),
        "satisfaction_score": random.randint(1, 5),
        "subscription_type": random.choice(["DIAMOND", "GOLD", "SILVER", "PLATINUM"]),
        "points_earned": random.randint(100, 1000),
        "timestamp": datetime.now().isoformat()
    }


async def send_client(client: httpx.AsyncClient, data: dict) -> None:
    try:
        response = await client.post(API_URL, json=data)
        if response.status_code == 200:
            print(f"✅ Отправлен {data['user_id']}")
        else:
            print(f"❌ Ошибка {data['user_id']}: {response.status_code}")
    except Exception as e:
        print(f"💥 Не удалось подключиться: {e}")


async def run_simulator():
    print(f"🚀 Запуск симулятора — {NUM_CLIENTS} клиентов\n")
    async with httpx.AsyncClient() as client:
        for i in range(NUM_CLIENTS):
            data = generate_client()
            await send_client(client, data)
            await asyncio.sleep(DELAY_SECONDS)
    print(f"\n✅ Готово — отправлено {NUM_CLIENTS} клиентов")


if __name__ == "__main__":
    asyncio.run(run_simulator())
