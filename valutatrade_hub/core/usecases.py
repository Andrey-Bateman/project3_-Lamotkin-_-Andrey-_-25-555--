import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from .models import User, Portfolio, Wallet
from .utils import load_json, save_json, generate_salt
from .exceptions import CurrencyNotFoundError, InsufficientFundsError, ApiRequestError
from .currencies import get_currency
from ..infra.database import DatabaseManager
from ..decorators import log_action

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
    reg_date = datetime.now()
    user_data = {
        'user_id': user_id,
        'username': username,
        'hashed_password': hashed_password,
        'salt': salt,
        'registration_date': reg_date.isoformat()
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
                wallets_dict[code] = Wallet(w_data['currency_code'], w_data['balance'])
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
                    'currency_code': wallet.currency_code,
                    'balance': wallet.balance
                }
            portfolios[i]['wallets'] = wallets_data
            db.save_collection('portfolios.json', portfolios)
            return
    create_portfolio(portfolio.user_id)
    save_portfolio(portfolio)

@log_action('BUY', verbose=True)
def buy(user_id: int, currency_code: str, amount: float) -> None:
    get_currency(currency_code)
    db = DatabaseManager()
    portfolio = db.get_portfolio(user_id) or Portfolio(user_id)
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
    db.save_portfolio(portfolio)
    return f"Cost: {cost:.2f} USD"

@log_action('SELL', verbose=True)
def sell(user_id: int, currency_code: str, amount: float) -> None:
    get_currency(currency_code)
    db = DatabaseManager()
    portfolio = db.get_portfolio(user_id)
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
    usd_wallet = portfolio.get_wallet('USD')
    if not usd_wallet:
        portfolio.add_currency('USD')
        usd_wallet = portfolio.get_wallet('USD')
    usd_wallet.deposit(revenue)
    db.save_portfolio(portfolio)
    return f"Revenue: {revenue:.2f} USD"

def get_rate(from_code: str, to_code: str) -> float:
    get_currency(from_code)
    get_currency(to_code)
    settings = SettingsLoader()
    ttl = settings.get('rates_ttl_seconds', 300)
    rate = get_exchange_rate(from_code, to_code)
    if rate is None:
        raise ApiRequestError('No data available')
    return rate
