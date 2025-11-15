import requests
from abc import ABC, abstractmethod
from typing import Dict
from .config import ParserConfig
from ..core.exceptions import ApiRequestError

class BaseApiClient(ABC):
    @abstractmethod
    def fetch_rates(self, base_currency: str) -> Dict[str, float]:
        pass

class CoinGeckoClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config
        self.url = config.COINGECKO_URL
        self.api_key = config.COINGECKO_API_KEY
        self.timeout = config.REQUEST_TIMEOUT

    def fetch_rates(self, base_currency: str) -> Dict[str, float]:
        ids = [self.config.CRYPTO_ID_MAP[code] for code in self.config.CRYPTO_CURRENCIES]
        params = {'ids': ','.join(ids), 'vs_currencies': base_currency.lower()}
        headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {} 
        try:
            response = requests.get(self.url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            rates = {}
            for code in self.config.CRYPTO_CURRENCIES:
                id_key = self.config.CRYPTO_ID_MAP[code]
                if id_key in data and base_currency.lower() in data[id_key]:
                    rates[f"{code}_{base_currency}"] = data[id_key][base_currency.lower()]
            return rates
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko error: {str(e)}")

class ExchangeRateApiClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config
        self.url = config.EXCHANGERATE_API_URL
        self.api_key = config.EXCHANGERATE_API_KEY
        self.timeout = config.REQUEST_TIMEOUT

    def fetch_rates(self, base_currency: str) -> Dict[str, float]:
        endpoint = f"{self.url}/{self.api_key}/latest/{base_currency}" 
        try:
            response = requests.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            print(f"Debug ExchangeRate response: {data}")  
            if data.get('result') != 'success':
                raise ApiRequestError(f"ExchangeRate-API error: {data.get('error-type', 'Unknown')}")
            if 'conversion_rates' not in data:  
                raise ApiRequestError(f"Invalid response structure: missing 'conversion_rates' key. Response: {data}")
            rates = {}
            for code in self.config.FIAT_CURRENCIES:
                if code in data['conversion_rates']: 
                    rates[f"{code}_{base_currency}"] = data['conversion_rates'][code] 
            return rates
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API error: {str(e)}")
