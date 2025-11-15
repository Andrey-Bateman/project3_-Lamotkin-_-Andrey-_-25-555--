from abc import ABC, abstractmethod
from typing import Dict
from .exceptions import CurrencyNotFoundError

class Currency(ABC):
    def __init__(self, name: str, code: str):
        if not name or not isinstance(name, str):
            raise ValueError("Name не может быть пустым")
        if not code or not isinstance(code, str) or len(code) < 2 or len(code) > 5 or not code.isupper() or ' ' in code:
            raise ValueError("Code — верхний регистр, 2–5 символов, без пробелов")
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        pass

CURRENCY_REGISTRY: Dict[str, type[Currency]] = {}

class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 0 else "N/A"
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"

CURRENCY_REGISTRY = {
    'USD': lambda: FiatCurrency("US Dollar", "USD", "United States"),
    'EUR': lambda: FiatCurrency("Euro", "EUR", "Eurozone"),
    'RUB': lambda: FiatCurrency("Russian Ruble", "RUB", "Russia"),
    'BTC': lambda: CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    'ETH': lambda: CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
}

def get_currency(code: str) -> Currency:
    code_upper = code.upper()
    if code_upper not in CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code_upper)
    return CURRENCY_REGISTRY[code_upper]()
