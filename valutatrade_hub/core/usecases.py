import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from .models import User, Portfolio, Wallet
from .utils import load_json, save_json, generate_salt, get_exchange_rate
from .exceptions import CurrencyNotFoundError, InsufficientFundsError, ApiRequestError
from .currencies import get_currency
from ..infra.database import DatabaseManager
from ..decorators import log_action
from ..infra.settings import SettingsLoader

def create_user(username: str, password: str) -> Optional[User]:
    db = DatabaseManager()
    users = db.get_collection('users.json')
    if any(u['username'] == username for u in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    user_id = max([u['user_id'] for u in users], default=0) + 1
    salt = generate_salt()
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
    reg_date = datetime.now(timezone.utc)  
    user_data = {
        'user_id': user_id,
        'username': username,
        'hashed_password': hashed_password,
        'salt': salt,
        'registration_date': reg_date.isoformat(timespec='milliseconds') 
    }
    users.append(user_data)
    db.save_collection('users.json', users)
    create_portfolio(user_id)
    return User(user_id, username, hashed_password, salt, reg_date)

def get_user_by_username(username: str) -> Optional[User]:
    db = DatabaseManager()
    users = db.get_collection('users.json')
    for u_data in users:
        if u_data['username'] == username:
            reg_date = u_data['registration_date']
            if isinstance(reg_date, str):
                reg_date = datetime.fromisoformat(reg_date)  
            return User(
                u_data['user_id'],
                u_data['username'],
                u_data['hashed_password'],
                u_data['salt'],
                reg_date
            )
    return None


def verify_user_login(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if user and user.verify_password(password):
        return user
    return None

def get_user_by_id(user_id: int) -> Optional[User]:
    db = DatabaseManager()
    users = db.get_collection('users.json')
    for u_data in users:
        if u_data['user_id'] == user_id:
            reg_date = u_data['registration_date']
            if isinstance(reg_date, str):
                reg_date = datetime.fromisoformat(reg_date) 
            return User(
                u_data['user_id'],
                u_data['username'],
                u_data['hashed_password'],
                u_data['salt'],
                reg_date
            )
    return None


def create_portfolio(user_id: int) -> None:
    db = DatabaseManager()
    portfolios = db.get_collection('portfolios.json')
    if not any(p['user_id'] == user_id for p in portfolios):
        portfolios.append({'user_id': user_id, 'wallets': {}})
        db.save_collection('portfolios.json', portfolios)

def get_portfolio(user_id: int) -> Optional[Portfolio]:
    db = DatabaseManager()
    portfolios = db.get_collection('portfolios.json')
    for p_data in portfolios:
        if p_data['user_id'] == user_id:
            wallets_dict: Dict[str, Wallet] = {}
            for code, w_data in p_data['wallets'].items():
                wallets_dict[code] = Wallet(code, w_data['balance'])
            return Portfolio(user_id, wallets_dict)
    return None

def save_portfolio(portfolio: Portfolio) -> None:
    db = DatabaseManager()
    portfolios = db.get_collection('portfolios.json')
    for i, p in enumerate(portfolios):
        if p['user_id'] == portfolio.user_id:
            wallets_data: Dict[str, Dict[str, Any]] = {}
            for code, wallet in portfolio.wallets.items():
                wallets_data[code] = {
                    'currency_code': code,
                    'balance': wallet.balance
                }
            portfolios[i]['wallets'] = wallets_data
            db.save_collection('portfolios.json', portfolios)
            return
    create_portfolio(portfolio.user_id)
    save_portfolio(portfolio)

@log_action('BUY', verbose=True)
def buy(user_id: int, currency_code: str, amount: float) -> None:
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    get_currency(currency_code) 
    db = DatabaseManager()
    portfolio = get_portfolio(user_id) or Portfolio(user_id)
    wallet = portfolio.get_wallet(currency_code)
    if not wallet:
        portfolio.add_currency(currency_code)
        wallet = portfolio.get_wallet(currency_code)
    old_balance = wallet.balance
    wallet.deposit(amount)
    usd_rate = get_exchange_rate(currency_code, 'USD')
    if usd_rate is None and currency_code != 'USD':
        raise ApiRequestError('No rate data')
    cost = amount * usd_rate if usd_rate else amount
    rate_str = f"{usd_rate:.2f}" if usd_rate is not None else 'N/A'
    save_portfolio(portfolio)
    print(f"Покупка выполнена: {amount:.4f} {currency_code} по курсу {rate_str} USD/{currency_code}")
    print(f"Изменения в портфеле:\n- {currency_code}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
    print(f"Оценочная стоимость покупки: {cost:.2f} USD")
    return f"Cost: {cost:.2f} USD"

@log_action('SELL', verbose=True)
def sell(user_id: int, currency_code: str, amount: float) -> None:
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    get_currency(currency_code) 
    db = DatabaseManager()
    portfolio = get_portfolio(user_id)
    if not portfolio:
        raise ValueError("У вас нет портфеля.")
    wallet = portfolio.get_wallet(currency_code)
    if not wallet:
        raise CurrencyNotFoundError(currency_code)
    if amount > wallet.balance:
        raise InsufficientFundsError(wallet.balance, amount, currency_code)
    old_balance = wallet.balance
    wallet.withdraw(amount)
    usd_rate = get_exchange_rate(currency_code, 'USD')
    if usd_rate is None and currency_code != 'USD':
        raise ApiRequestError('No rate data')
    revenue = amount * usd_rate if usd_rate else amount
    rate_str = f"{usd_rate:.2f}" if usd_rate is not None else 'N/A'
    usd_wallet = portfolio.get_wallet('USD')
    if not usd_wallet:
        portfolio.add_currency('USD')
        usd_wallet = portfolio.get_wallet('USD')
    usd_wallet.deposit(revenue)
    save_portfolio(portfolio)
    print(f"Продажа выполнена: {amount:.4f} {currency_code} по курсу {rate_str} USD/{currency_code}")
    print(f"Изменения в портфеле:\n- {currency_code}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
    print(f"Оценочная выручка: {revenue:.2f} USD")
    return f"Revenue: {revenue:.2f} USD"

def get_rate(from_code: str, to_code: str) -> float:
    get_currency(from_code)
    get_currency(to_code)
    settings = SettingsLoader()
    ttl = settings.get('rates_ttl_seconds', 300)
    data = load_json('rates.json')
    key = f"{from_code}_{to_code}"
    if key in data:
        updated_at = data[key].get('updated_at')
        if updated_at:
            update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            if now - update_time > timedelta(seconds=ttl):
                raise ApiRequestError('Кеш устарел, требуется обновление API')
    rate = get_exchange_rate(from_code, to_code)
    if rate is None:
        raise ApiRequestError('Данные курса недоступны')
    return rate
