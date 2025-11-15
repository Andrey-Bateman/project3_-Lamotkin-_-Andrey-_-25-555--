import argparse
import sys
from typing import Optional
from prettytable import PrettyTable
from valutatrade_hub.core.usecases import (create_user, verify_user_login, get_portfolio, save_portfolio, get_user_by_id, buy, sell, get_rate)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import load_json, get_exchange_rate, load_session, save_session, clear_session 
from valutatrade_hub.core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError

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
            buy(current_user.user_id, args.currency.upper(), float(args.amount))
        elif args.command == 'sell':
            sell(current_user.user_id, args.currency.upper(), float(args.amount))
        elif args.command == 'get-rate':
            rate = get_rate(args.from_.upper(), args.to.upper())
            data = load_json('rates.json')
            key = f"{args.from_.upper()}_{args.to.upper()}"
            updated = data.get(key, {}).get('updated_at', 'unknown')
            print(f"Курс {args.from_.upper()}→{args.to.upper()}: {rate:.8f} (обновлено: {updated})")
            rev_rate = get_exchange_rate(args.to.upper(), args.from_.upper())
            if rev_rate:
                print(f"Обратный курс {args.to.upper()}→{args.from_.upper()}: {rev_rate:.2f}")
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
