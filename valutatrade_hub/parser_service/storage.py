import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from .config import ParserConfig

class RatesStorage:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.rates_path = Path(config.RATES_FILE_PATH)
        self.history_path = Path(config.HISTORY_FILE_PATH)

    def save_history_entry(self, entry: Dict) -> None:
        temp_path = self.history_path.with_suffix('.tmp')
        history = self.load_history() 
        history.append(entry)
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, default=str)
        temp_path.rename(self.history_path)

    def load_history(self) -> List[Dict]:
        if self.history_path.exists():
            with open(self.history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    print("Warning: history file is dict, converting to list")
                    return []
        return []

    def save_rates_cache(self, rates: Dict[str, float], source: str) -> None:
        timestamp = datetime.utcnow().isoformat() + 'Z'
        cache = self.load_rates_cache()
        for pair, rate in rates.items():
            cache[pair] = {'rate': rate, 'updated_at': timestamp, 'source': source}
        cache['last_refresh'] = timestamp
        temp_path = self.rates_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, default=str)
        temp_path.rename(self.rates_path)

    def load_rates_cache(self) -> Dict[str, Dict]:
        if self.rates_path.exists():
            with open(self.rates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
