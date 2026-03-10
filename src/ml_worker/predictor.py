"""
ML Predictor — загрузка CatBoost модели и инференс.

Особенности:
- Модель загружается ОДИН РАЗ при старте воркера (не на каждый запрос)
- Маппинг полей: входящий JSON (snake_case) → фичи модели (оригинальные имена)
- Категориальные фичи передаются как строки (CatBoost обрабатывает нативно)
"""

import os
import numpy as np
import pandas as pd
import traceback
from pathlib import Path
from catboost import CatBoostClassifier

from src.shared.config import settings


# ─────────────────────────────────────────────────────────────
# МАППИНГ: наши snake_case поля → оригинальные имена датасета
# ─────────────────────────────────────────────────────────────

FEATURE_MAP = {
    "credit_score":       "CreditScore",
    "geography":          "Geography",
    "gender":             "Gender",
    "age":                "Age",
    "tenure":             "Tenure",
    "balance":            "Balance",
    "num_of_products":    "NumOfProducts",
    "has_cr_card":        "HasCrCard",
    "is_active_member":   "IsActiveMember",
    "estimated_salary":   "EstimatedSalary",
    "complain":           "Complain",
    "satisfaction_score": "Satisfaction Score",
    "subscription_type":  "Card Type",
    "points_earned":      "Point Earned",
}

# Порядок фич ВАЖЕН — должен совпадать с тем, как обучали
FEATURE_ORDER = list(FEATURE_MAP.values())

# Категориальные фичи (CatBoost должен знать их имена)
CATEGORICAL_FEATURES = ["Geography", "Gender", "Card Type"]


class ChurnPredictor:
    """
    Синглтон-предиктор. Загружает модель один раз, переиспользует на каждый запрос.
    """

    def __init__(self):
        self.model: CatBoostClassifier | None = None
        self._model_path = Path(settings.MODEL_PATH.replace("\\", "/"))

    def load(self) -> None:
        """
        Загружает модель с диска. Вызывается один раз при старте воркера.
        Бросает исключение если файл не найден — это намеренно (fail fast).
        """
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"❌ Файл модели не найден: {self._model_path.absolute()}\n"
                f"   Текущая директория: {Path.cwd()}\n"
                f"   Запусти: python notebooks/train_model.py"
        )
        # if not os.path.exists(self._model_path):
        #     raise FileNotFoundError(
        #         f"❌ Файл модели не найден: {self._model_path}\n"
        #         f"   Запусти: python notebooks/train_model.py"
        #     )

        self.model = CatBoostClassifier()
        self.model.load_model(self._model_path)
        print(f"✅ CatBoost модель загружена: {self._model_path}")
        print(f"   Количество деревьев: {self.model.tree_count_}")

    def _prepare_features(self, raw_data: dict) -> pd.DataFrame:
        """
        Преобразует входящий словарь (из Kafka) в DataFrame с правильными именами колонок.
        
        Конвертации:
        - bool → int (CatBoost ожидает 0/1 для числовых фич)
        - subscription_type → Card Type (маппинг имён)
        """
        mapped = {}
        for our_key, model_key in FEATURE_MAP.items():
            value = raw_data[our_key]

            # bool → int для числовых булевых полей
            if isinstance(value, bool) and model_key not in CATEGORICAL_FEATURES:
                value = int(value)

            mapped[model_key] = value

        # Создаём DataFrame с правильным порядком колонок
        df = pd.DataFrame([mapped], columns=FEATURE_ORDER)
        return df

    def predict(self, raw_data: dict) -> float:
        """
        Принимает словарь из Kafka, возвращает float — вероятность оттока.
        
        Args:
            raw_data: словарь с полями из ClientChurnEvent
            
        Returns:
            float от 0.0 до 1.0 — вероятность что клиент уйдёт
            
        Raises:
            RuntimeError: если модель не загружена (load() не вызван)
            KeyError: если в raw_data отсутствует обязательная фича
        """
        if self.model is None:
            raise RuntimeError(
                "❌ Модель не загружена! Вызови predictor.load() при старте воркера."
            )

        features_df = self._prepare_features(raw_data)
        
        # predict_proba возвращает [[prob_class_0, prob_class_1]]
        # нам нужен prob_class_1 (вероятность оттока)
        proba = self.model.predict_proba(features_df)[0][[1]]
        
        return round(float(proba), 4)


# Синглтон — импортируем этот объект везде
predictor = ChurnPredictor()
