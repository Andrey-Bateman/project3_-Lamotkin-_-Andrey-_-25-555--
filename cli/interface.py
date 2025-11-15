import argparse
import sys
from typing import Optional
from prettytable import PrettyTable
from valutatrade_hub.core.usecases import (create_user, verify_user_login, get_portfolio, save_portfolio, get_user_by_id)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import load_json, get_exchange_rate, load_session, save_session, clear_session

current_user: Optional[User] = None

def register(args):
    try:
        user = create_user(args.username, args.password)
        print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). Войдите: login --username {user.username} --password ****")
    except ValueError as e:
        print(str(e))

def login(args):
    global current_user
    try:
        user = verify_user_login(args.username, args.password)
        if user:
            current_user = user
            save_session(user.user_id)  
            print(f"Вы вошли как '{user.username}'")
        else:
            print("Неверный пароль")
    except ValueError as e:
        print(str(e) or "Пользователь не найден")

def show_portfolio(args):
    global current_user
    if not current_user:
        print("Сначала выполните login")
        return
    try:
        base = (args.base or 'USD').upper()
        portfolio = get_portfolio(current_user.user_id)
        if not portfolio or not portfolio.wallets:
            print("У вас нет портфеля или кошельков.")
            return
        table = PrettyTable(['Currency', 'Balance', f'Value in {base}'])
        total = portfolio.get_total_value(base)
        for code, wallet in portfolio.wallets.items():
            if code == base:
                value = wallet.balance
            else:
                rate = get_exchange_rate(code, base)
                value = wallet.balance * (rate or 1.0)
            table.add_row([code, f"{wallet.balance:.4f}", f"{value:.2f}"])
        print(f"Портфель пользователя '{current_user.username}' (база: {base}):")
        print(table)
        print(f"---------------------------------\nИТОГО: {total:.2f} {base}")
    except ValueError as e:
        print(str(e) or f"Неизвестная базовая валюта '{args.base}'")

def buy(args):
    global current_user
    if not current_user:
        print("Сначала выполните login")
        return
    try:
        currency = args.currency.upper()
        amount = float(args.amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        portfolio = get_portfolio(current_user.user_id) or Portfolio(current_user.user_id)
        wallet = portfolio.get_wallet(currency)
        if not wallet:
            portfolio.add_currency(currency)
            wallet = portfolio.get_wallet(currency)
        old_balance = wallet.balance
        wallet.deposit(amount)
        usd_rate = get_exchange_rate(currency, 'USD')
        if usd_rate is None and currency != 'USD':
            raise ValueError(f"Не удалось получить курс для {currency}→USD")
        cost = amount * usd_rate if usd_rate is not None else amount
        rate_str = f"{usd_rate:.2f}" if usd_rate is not None else 'N/A'
        save_portfolio(portfolio)
        print(f"Покупка выполнена: {amount:.4f} {currency} по курсу {rate_str} USD/{currency}")
        print(f"Изменения в портфеле:\n- {currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
        print(f"Оценочная стоимость покупки: {cost:.2f} USD")
    except ValueError as e:
        print(str(e))

def sell(args):
    global current_user
    if not current_user:
        print("Сначала выполните login")
        return
    try:
        currency = args.currency.upper()
        amount = float(args.amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        portfolio = get_portfolio(current_user.user_id)
        if not portfolio:
            raise ValueError("У вас нет портфеля.")
        wallet = portfolio.get_wallet(currency)
        if not wallet:
            raise ValueError(f"У вас нет кошелька '{currency}'. Добавьте валюту: она создаётся автоматически при первой покупке.")
        old_balance = wallet.balance
        wallet.withdraw(amount)
        usd_rate = get_exchange_rate(currency, 'USD')
        if usd_rate is None and currency != 'USD':
            raise ValueError(f"Не удалось получить курс для {currency}→USD")
        revenue = amount * usd_rate if usd_rate is not None else amount
        rate_str = f"{usd_rate:.2f}" if usd_rate is not None else 'N/A'
     
        usd_wallet = portfolio.get_wallet('USD')
        if not usd_wallet:
            portfolio.add_currency('USD')
            usd_wallet = portfolio.get_wallet('USD')
        usd_wallet.deposit(revenue)
        save_portfolio(portfolio)
        print(f"Продажа выполнена: {amount:.4f} {currency} по курсу {rate_str} USD/{currency}")
        print(f"Изменения в портфеле:\n- {currency}: было {old_balance:.4f} → стало {wallet.balance:.4f}")
        print(f"Оценочная выручка: {revenue:.2f} USD")
    except ValueError as e:
        print(str(e))

def get_rate(args):
    try:
        from_curr = args.from_.upper()  #
        to_curr = args.to.upper()
        rate = get_exchange_rate(from_curr, to_curr)
        if rate is None:
            raise ValueError(f"Курс {from_curr}→{to_curr} недоступен. Повторите попытку позже.")
        data = load_json('rates.json')
        key = f"{from_curr}_{to_curr}"
        updated = data.get(key, {}).get('updated_at', 'unknown')
        print(f"Курс {from_curr}→{to_curr}: {rate:.8f} (обновлено: {updated})")
        rev_rate = get_exchange_rate(to_curr, from_curr)
        if rev_rate:
            print(f"Обратный курс {to_curr}→{from_curr}: {rev_rate:.2f}")
    except ValueError as e:
        print(str(e))

def logout(args):
    global current_user
    current_user = None
    clear_session()
    print("Вы вышли из системы")

def main():
    global current_user
    session_id = load_session()
    if session_id:
        user = get_user_by_id(session_id)
        if user:
            current_user = user
        else:
            clear_session()

    parser = argparse.ArgumentParser(description='ValutaTrade Hub CLI')
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    reg = subparsers.add_parser('register', help='Регистрация нового пользователя')
    reg.add_argument('--username', required=True, help='Имя пользователя (уникальное)')
    reg.add_argument('--password', required=True, help='Пароль (минимум 4 символа)')
    log = subparsers.add_parser('login', help='Вход в систему')
    log.add_argument('--username', required=True)
    log.add_argument('--password', required=True)
    pf = subparsers.add_parser('show-portfolio', help='Показать портфель')
    pf.add_argument('--base', default='USD', help='Базовая валюта для конвертации (по умолчанию USD)')
    buy_p = subparsers.add_parser('buy', help='Купить валюту')
    buy_p.add_argument('--currency', required=True, help='Код валюты (e.g., BTC, EUR)')
    buy_p.add_argument('--amount', type=float, required=True, help='Количество для покупки')
    sell_p = subparsers.add_parser('sell', help='Продать валюту')
    sell_p.add_argument('--currency', required=True, help='Код валюты')
    sell_p.add_argument('--amount', type=float, required=True, help='Количество для продажи')
    rate_p = subparsers.add_parser('get-rate', help='Получить курс валют')
    rate_p.add_argument('--from', dest='from_', required=True, help='Исходная валюта (e.g., USD)')
    rate_p.add_argument('--to', required=True, help='Целевая валюта (e.g., BTC)')
    logout_p = subparsers.add_parser('logout', help='Выход из системы')
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    try:
        if args.command == 'register':
            register(args)
        elif args.command == 'login':
            login(args)
        elif args.command == 'show-portfolio':
            show_portfolio(args)
        elif args.command == 'buy':
            buy(args)
        elif args.command == 'sell':
            sell(args)
        elif args.command == 'get-rate':
            get_rate(args)
        elif args.command == 'logout':
            logout(args)
    except InsufficientFundsError as e:
        print(str(e))
    except CurrencyNotFoundError as e:
        print(str(e))
        print("Поддерживаемые коды: USD, EUR, RUB, BTC, ETH. Используйте help get-rate.")
    except ApiRequestError as e:
        print(str(e))
        print("Повторите попытку позже или проверьте сеть.")
    except ValueError as e:
        print(f"Ошибка валидации: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

if __name__ == '__main__':
    main()
