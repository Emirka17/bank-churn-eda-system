"""
Baseline обучение CatBoost модели для предсказания оттока клиентов.

Использование:
    1. Скачай датасет с Kaggle:
       https://www.kaggle.com/competitions/bank-customer-churn-ict-u-ai
       Положи train.csv в папку notebooks/data/

    2. Запусти из КОРНЯ проекта:
       python notebooks/train_model.py

    3. Модель сохранится в: models/churn_model.cbm
"""

import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

# ─────────────────────────────────────────────
# КОНСТАНТЫ
# ─────────────────────────────────────────────

DATA_PATH = "data/Customer_Churn_Records_test.csv"
MODEL_OUTPUT_PATH = "models/churn_model.cbm"

# Фичи которые используем (дропаем мусор: RowNumber, CustomerId, Surname)
FEATURE_COLUMNS = [
    "CreditScore",
    "Geography",
    "Gender",
    "Age",
    "Tenure",
    "Balance",
    "NumOfProducts",
    "HasCrCard",
    "IsActiveMember",
    "EstimatedSalary",
    "Complain",
    "Satisfaction Score",
    "Card Type",
    "Point Earned",
]

TARGET_COLUMN = "Exited"

# Категориальные фичи — CatBoost умеет с ними работать нативно, без LabelEncoder
CATEGORICAL_FEATURES = ["Geography", "Gender", "Card Type"]


# ─────────────────────────────────────────────
# ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ
# ─────────────────────────────────────────────

def load_and_prepare(path: str) -> tuple[pd.DataFrame, pd.Series]:
    print(f"📂 Загружаем данные из {path}...")
    df = pd.read_csv(path)

    print(f"   Размер датасета: {df.shape}")
    print(f"   Распределение таргета:\n{df[TARGET_COLUMN].value_counts(normalize=True).round(3)}")

    # Проверяем что все нужные колонки есть
    missing = [col for col in FEATURE_COLUMNS + [TARGET_COLUMN] if col not in df.columns]
    if missing:
        raise ValueError(f"❌ В датасете отсутствуют колонки: {missing}")

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    return X, y


# ─────────────────────────────────────────────
# ОБУЧЕНИЕ
# ─────────────────────────────────────────────

def train(X: pd.DataFrame, y: pd.Series) -> CatBoostClassifier:
    print("\n🔀 Разбиваем на train/validation (80/20)...")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y  # важно при дисбалансе классов
    )
    print(f"   Train: {X_train.shape[0]} | Val: {X_val.shape[0]}")

    # CatBoost Pool — эффективная структура данных для обучения
    train_pool = Pool(
        data=X_train,
        label=y_train,
        cat_features=CATEGORICAL_FEATURES
    )
    val_pool = Pool(
        data=X_val,
        label=y_val,
        cat_features=CATEGORICAL_FEATURES
    )

    print("\n🧠 Обучаем CatBoost (baseline параметры)...")
    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        loss_function="Logloss",       # бинарная классификация
        eval_metric="AUC",
        random_seed=42,
        early_stopping_rounds=50,      # останавливаемся если нет улучшений
        verbose=100,                   # печатаем прогресс каждые 100 итераций
        class_weights={0: 1, 1: 4},   # датасет несбалансированный (~20% churn)
    )

    model.fit(
        train_pool,
        eval_set=val_pool,
        use_best_model=True  # берём лучшую итерацию по val AUC
    )

    # ─── Метрики ───
    print("\n📊 Результаты на Validation set:")
    y_pred_proba = model.predict_proba(X_val)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_val, y_pred_proba)
    print(f"   ROC-AUC: {auc:.4f}")
    print("\n   Classification Report:")
    print(classification_report(y_val, y_pred, target_names=["Stay", "Churn"]))

    # ─── Feature Importance (топ-10) ───
    print("\n🔍 Feature Importance (топ-10):")
    fi = pd.Series(
        model.get_feature_importance(),
        index=FEATURE_COLUMNS
    ).sort_values(ascending=False)
    print(fi.head(10).to_string())

    return model


# ─────────────────────────────────────────────
# СОХРАНЕНИЕ
# ─────────────────────────────────────────────

def save_model(model: CatBoostClassifier, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    model.save_model(path)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"\n✅ Модель сохранена: {path} ({size_mb:.2f} MB)")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Bank Churn — CatBoost Baseline Training")
    print("=" * 50)

    X, y = load_and_prepare(DATA_PATH)
    model = train(X, y)
    save_model(model, MODEL_OUTPUT_PATH)

    print("\n🚀 Готово! Следующий шаг: запустить ML Worker с реальной моделью.")
    print(f"   Путь к модели: {MODEL_OUTPUT_PATH}")
