import schedule
import time
from typing import Callable
from .config import ParserConfig
from .updater import RatesUpdater

class RateScheduler:
    def __init__(self, config: ParserConfig, update_func: Callable):
        self.config = config
        self.updater = RatesUpdater(config)
        self.update_func = update_func
        self.interval_min = config.rates_ttl_seconds / 60  

    def start(self):
        schedule.every(self.interval_min).minutes.do(self.update_func)
        logger.info(f"Scheduler started: update every {self.interval_min} min")
        while True:
            schedule.run_pending()
            time.sleep(60)  

    def run_once(self):
        self.update_func()
