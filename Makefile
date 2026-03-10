# Makefile
.PHONY: help dev prod build train train-in-container

help:
	@echo "Доступные команды:"
	@echo "  make dev              - Запуск в режиме разработки (с volumes)"
	@echo "  make prod             - Сборка продакшен образа (с моделью внутри)"
	@echo "  build                 - Сборка образа"
	@echo "  train                 - Обучение модели локально"
	@echo "  train-in-container    - Обучение модели внутри контейнера"
	@echo "  logs                  - Просмотр логов ml_worker"
	@echo "  shell                 - Вход в контейнер ml_worker"

dev:
	@echo "🚀 Запуск в режиме разработки..."
	docker-compose up -d
	@echo "✅ Готово! Смотри логи: make logs"

prod:
	@echo "📦 Сборка продакшен образа..."
	# Сначала обучаем модель (если нужно)
	python notebooks/train_model.py --output ./models/churn_model.cbm
	# Собираем образ с моделью
	docker build -t bank-ml-worker:latest --target production .
	@echo "✅ Продакшен образ готов: bank-ml-worker:latest"

build:
	docker-compose build

train:
	@echo "📚 Обучение модели..."
	python notebooks/train_model.py --output ./models/churn_model.cbm
	@echo "✅ Модель сохранена в ./models/churn_model.cbm"

train-in-container:
	@echo "📚 Обучение модели в контейнере..."
	docker exec bank_ml_worker python notebooks/train_model.py
	@echo "✅ Модель обучена"

logs:
	docker logs -f bank_ml_worker

shell:
	docker exec -it bank_ml_worker bash

# Для CI/CD
ci-build:
	@echo "🔧 CI сборка..."
	python notebooks/train_model.py --output ./models/churn_model.cbm
	docker build -t bank-ml-worker:$${VERSION:-latest} --target production .
