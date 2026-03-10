import random

class ChurnPredictor:
    def __init__(self):
        # На будущее: self.model = load_model(...)
        pass

    def predict(self, features: dict) -> float:
        """
        Принимает словарь со всеми фичами из ClientActivityEvent 
        и возвращает float (вероятность ухода клиента).
        """
        # Пока возвращаем случайную вероятность оттока
        return round(random.uniform(0.0, 1.0), 4)

predictor = ChurnPredictor()
