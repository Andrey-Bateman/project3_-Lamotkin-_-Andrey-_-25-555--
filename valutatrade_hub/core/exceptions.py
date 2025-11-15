from typing import Optional

class CurrencyNotFoundError(ValueError):
    def __init__(self, code: str):
        super().__init__(f"Неизвестная валюта '{code}'")
        self.code = code

class InsufficientFundsError(ValueError):
    def __init__(self, available: float, required: float, code: str):
        super().__init__(f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}")
        self.available = available
        self.required = required
        self.code = code

class ApiRequestError(ValueError):
    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
        self.reason = reason
