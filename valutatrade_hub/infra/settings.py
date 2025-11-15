import json
from typing import Any, Dict
from pathlib import Path

class SingletonMeta(type):
    _instances: Dict[type, 'SettingsLoader'] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class SettingsLoader(metaclass=SingletonMeta):
    def __init__(self):
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config_path = Path('config.json')
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Ошибка в config.json — используем дефолт")
        return {
            'data_dir': 'data',
            'rates_ttl_seconds': 300,  
            'default_base': 'USD',
            'log_level': 'INFO',
            'supported_currencies': ['USD', 'EUR', 'RUB', 'BTC', 'ETH']
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def reload(self) -> None:
        self._config = self._load_config()
