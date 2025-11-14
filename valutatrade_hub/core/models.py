import hashlib  
from datetime import datetime  
from typing import Optional  
from typing import Dict
from .utils import get_exchange_rate

class User:
    def __init__(self, user_id: int, username: str, hashed_password: str, salt: str, registration_date: datetime):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        if not self._username:  
            raise ValueError("Имя пользователя не может быть пустым")
        return self._username

    @username.setter
    def username(self, value: str):
        if not value or not isinstance(value, str):  
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> str:
        return f"ID: {self._user_id}, Username: {self._username}, Registered: {self._registration_date.isoformat()}"

    def change_password(self, new_password: str) -> None:
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._salt = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]
        self._hashed_password = hashlib.sha256((new_password + self._salt).encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        hashed = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hashed == self._hashed_password


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        if not currency_code or not isinstance(currency_code, str):
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.upper()  
        self._balance = float(balance)  

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self._balance:
            raise ValueError(f"Недостаточно средств: доступно {self._balance}, требуется {amount}")
        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self._balance:.4f}"  

class Portfolio:
    def __init__(self, user_id: int, wallets: Dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets or {}  

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> Optional[User]:
        from .usecases import get_user_by_id
        return get_user_by_id(self._user_id)
    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> None:
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError("Код валюты уже существует в портфеле")
        self._wallets[code] = Wallet(code)  

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        code = currency_code.upper()
        return self._wallets.get(code)

    def get_total_value(self, base_currency: str = 'USD') -> float:
        base_code = base_currency.upper()
        total = 0.0
        exchange_rates = {
            'EUR': 1.0786,  
            'BTC': 59337.21,
            'RUB': 0.01016,
            'ETH': 3720.00,
           
        }
        for code, wallet in self._wallets.items():
            if code == base_code:
                total += wallet.balance
            else:
                rate = get_exchange_rate(code, base_code)
                if rate is None:
                    rate = 1.0  
                total += wallet.balance * rate
        return total
