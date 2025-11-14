import json  
import os    
from datetime import datetime, timedelta  
from typing import Dict, Any, Optional, Union, List
DATA_DIR = 'data'

EXCHANGE_RATES = {
    'EUR_USD': 1.0786,     
    'BTC_USD': 59337.21,   
    'RUB_USD': 0.01016,    
    'ETH_USD': 3720.00,    
    'USD_EUR': 1 / 1.0786,
    'USD_BTC': 1 / 59337.21,
    'USD_RUB': 1 / 0.01016,
    'USD_ETH': 1 / 3720.00,
}

def load_json(filename: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if 'registration_date' in item:
                        item['registration_date'] = datetime.fromisoformat(item['registration_date'])
            return data
    return [] if 'users' in filename or 'portfolios' in filename else {}

def save_json(filename: str, data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> None:
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)  
    data_copy = data.copy() if isinstance(data, dict) else [item.copy() for item in data]
    if isinstance(data_copy, list):
        for item in data_copy:
            if 'registration_date' in item and isinstance(item['registration_date'], datetime):
                item['registration_date'] = item['registration_date'].isoformat()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data_copy, f, indent=2, ensure_ascii=False)  

def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    key = f"{from_currency.upper()}_{to_currency.upper()}"
    data = load_json('rates.json')  
    if key in data:
        updated_at = data[key].get('updated_at')
        if updated_at:
            update_time = datetime.fromisoformat(updated_at)
            if datetime.now() - update_time < timedelta(minutes=5):
                return data[key]['rate']
    
    rate = EXCHANGE_RATES.get(key)
    if rate is not None:
        if key not in data:
            data[key] = {}
        data[key]['rate'] = rate
        data[key]['updated_at'] = datetime.now().isoformat()
        data['last_refresh'] = datetime.now().isoformat()
        data['source'] = 'MockParser'  
        save_json('rates.json', data)
        return rate
    return None  

def generate_salt() -> str:
    import hashlib  
    return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]
