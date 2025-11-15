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

def update_rates(args):
    from valutatrade_hub.parser_service.config import ParserConfig
    from valutatrade_hub.parser_service.updater import RatesUpdater
    config = ParserConfig()
    updater = RatesUpdater(config)
    if args.source == 'coingecko':
        crypto_rates = updater.coingecko.fetch_rates(config.BASE_CURRENCY)
        updater.storage.save_rates_cache(crypto_rates, 'CoinGecko')
        print(f"Обновлено CoinGecko: {len(crypto_rates)} курсов")
    elif args.source == 'exchangerate':
        fiat_rates = updater.exrate.fetch_rates(config.BASE_CURRENCY)
        updater.storage.save_rates_cache(fiat_rates, 'ExchangeRate-API')
        print(f"Обновлено ExchangeRate-API: {len(fiat_rates)} курсов")
    else:
        result = updater.run_update()
        print(f"Обновление успешно. Всего обновлено курсов: {result['updated']}. Ошибок: {result['errors']}")
        if result['errors']:
            print("Проверьте логи для деталей.")

def show_rates(args):
    data = load_json('rates.json')
    if not data:
        print("Локальный кеш курсов пуст. Выполните 'update-rates'.")
        return
    pairs = data if 'pairs' not in data else data['pairs']
    base = (args.base or 'USD').upper()
    if args.currency:
        key = f"{args.currency.upper()}_{base}"
        if key in pairs:
            pair = pairs[key]
            print(f"Курс {args.currency.upper()}→{base}: {pair['rate']} (обновлено: {pair['updated_at']}, {pair['source']})")
        else:
            print(f"Курс для '{args.currency}' не найден в кеше.")
        return
    if args.top:
        crypto_pairs = {k: v for k, v in pairs.items() if k.endswith('_USD') and k.startswith(('BTC', 'ETH', 'SOL'))}
        sorted_crypto = sorted(crypto_pairs.items(), key=lambda x: (x[1]['rate'], x[0]), reverse=True)[:args.top]  
        print(f"Top {args.top} крипто (база USD):")
        for pair_key, pair in sorted_crypto:
            print(f"- {pair_key}: {pair['rate']} ({pair['source']})")
    else:
        print(f"Все курсы (база {base}):")
        for pair_key, pair in pairs.items():
            if pair_key.endswith(f"_{base}"):
                print(f"- {pair_key}: {pair['rate']} ({pair['source']}, {pair['updated_at']})")


def get_rate(args):
    try:
        from_curr = args.from_.upper()
        to_curr = args.to.upper()
        rate = get_rate(from_curr, to_curr) 
        data = load_json('rates.json')
        key = f"{from_curr}_{to_curr}"
        updated = data.get(key, {}).get('updated_at', 'unknown')
        print(f"Курс {from_curr}→{to_curr}: {rate:.8f} (обновлено: {updated})")
        rev_rate = get_exchange_rate(to_curr, from_curr)
        if rev_rate:
            print(f"Обратный курс {to_curr}→{from_curr}: {rev_rate:.2f}")
    except ValueError as e:
        print(str(e))

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
    update_p = subparsers.add_parser('update-rates', help='Обновить курсы')
    update_p.add_argument('--source', choices=['coingecko', 'exchangerate', 'all'], default='all', help='Источник (default: all)')
    show_rates_p = subparsers.add_parser('show-rates', help='Показать курсы')
    show_rates_p.add_argument('--currency', help='Курс для валюты')
    show_rates_p.add_argument('--top', type=int, help='Top N крипты')
    show_rates_p.add_argument('--base', default='USD', help='База')

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
            get_rate(args)
        elif args.command == 'logout':
            logout(args)
        elif args.command == 'update-rates':
            update_rates(args)
        elif args.command == 'show-rates':
            show_rates(args)
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
