import hashlib  
from datetime import datetime
from typing import Optional, List, Dict, Any
from .models import User, Portfolio, Wallet  
from .utils import load_json, save_json, generate_salt  


def create_user(username: str, password: str) -> Optional[User]:
    users = load_json('users.json')  
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
    save_json('users.json', users)
    create_portfolio(user_id)
    return User(user_id, username, hashed_password, salt, reg_date)

def get_user_by_username(username: str) -> Optional[User]:
    users = load_json('users.json')
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
    users = load_json('users.json')
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
    portfolios = load_json('portfolios.json')
    if not any(p['user_id'] == user_id for p in portfolios):
        portfolios.append({'user_id': user_id, 'wallets': {}})
        save_json('portfolios.json', portfolios)

def get_portfolio(user_id: int) -> Optional[Portfolio]:
    portfolios = load_json('portfolios.json')
    for p_data in portfolios:
        if p_data['user_id'] == user_id:
            wallets_dict: Dict[str, Wallet] = {}
            for code, w_data in p_data['wallets'].items():
                wallets_dict[code] = Wallet(w_data['currency_code'], w_data['balance'])
            return Portfolio(user_id, wallets_dict)
    return None

def save_portfolio(portfolio: Portfolio) -> None:
    portfolios = load_json('portfolios.json')
    for i, p in enumerate(portfolios):
        if p['user_id'] == portfolio.user_id:
            wallets_data: Dict[str, Dict[str, Any]] = {}
            for code, wallet in portfolio.wallets.items():
                wallets_data[code] = {
                    'currency_code': wallet.currency_code,
                    'balance': wallet.balance
                }
            portfolios[i]['wallets'] = wallets_data
            save_json('portfolios.json', portfolios)
            return
    create_portfolio(portfolio.user_id)
    save_portfolio(portfolio)  
