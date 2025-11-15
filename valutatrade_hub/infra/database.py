from typing import Dict, Any, Optional, List
from pathlib import Path
from .settings import SettingsLoader, SingletonMeta  
from ..core.utils import load_json, save_json  

class DatabaseManager(metaclass=SingletonMeta):
    def __init__(self):
        self.settings = SettingsLoader()
        self.data_dir = Path(self.settings.get('data_dir', 'data'))
        self.data_dir.mkdir(exist_ok=True)  

    def get_collection(self, filename: str) -> List[Dict[str, Any]] or Dict[str, Any]:
        path = self.data_dir / filename
        if path.exists():
            return load_json(filename)
        return [] if 'users' in filename or 'portfolios' in filename else {}

    def save_collection(self, filename: str, data: List[Dict[str, Any]] or Dict[str, Any]) -> None:
        save_json(filename, data)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        users = self.get_collection('users.json')
        for u in users:
            if u.get('user_id') == user_id:
                return u
        return None

