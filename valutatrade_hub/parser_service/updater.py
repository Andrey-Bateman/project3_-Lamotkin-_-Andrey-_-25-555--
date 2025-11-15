import logging
from datetime import datetime
from typing import Dict
from .config import ParserConfig
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RatesStorage
from ..core.exceptions import ApiRequestError 

logger = logging.getLogger(__name__)

class RatesUpdater:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.coingecko = CoinGeckoClient(config)
        self.exrate = ExchangeRateApiClient(config)
        self.storage = RatesStorage(config)

    def run_update(self) -> Dict[str, int]:
        logger.info("Starting rates update...")
        all_rates = {}
        errors = 0

        try:
            fiat_rates = self.exrate.fetch_rates(self.config.BASE_CURRENCY)
            all_rates.update(fiat_rates)
            logger.info(f"Fetched from ExchangeRate-API (key: {self.config.EXCHANGERATE_API_KEY[:8]}...): {len(fiat_rates)} rates")
        except ApiRequestError as e:
            logger.error(f"Failed ExchangeRate-API: {e}")
            errors += 1

        try:
            crypto_rates = self.coingecko.fetch_rates(self.config.BASE_CURRENCY)
            all_rates.update(crypto_rates)
            logger.info(f"Fetched from CoinGecko (key: {self.config.COINGECKO_API_KEY[:8]}...): {len(crypto_rates)} rates")
        except ApiRequestError as e:
            logger.error(f"Failed CoinGecko: {e}")
            errors += 1

        
        if all_rates:
            timestamp = datetime.utcnow().isoformat() + 'Z'
            for pair, rate in all_rates.items():
                from_curr, to_curr = pair.split('_')
                entry = {
                    'id': f"{pair}_{timestamp}",
                    'from_currency': from_curr,
                    'to_currency': to_curr,
                    'rate': rate,
                    'timestamp': timestamp,
                    'source': 'ExchangeRate-API' if from_curr in self.config.FIAT_CURRENCIES else 'CoinGecko',
                    'meta': {'request_ms': 0, 'status_code': 200} 
                }
                self.storage.save_history_entry(entry)
            self.storage.save_rates_cache(all_rates, 'ParserService')
            logger.info(f"Saved {len(all_rates)} rates to cache/history")
        else:
            logger.warning("No rates fetched — nothing saved")

        return {'updated': len(all_rates), 'errors': errors}
