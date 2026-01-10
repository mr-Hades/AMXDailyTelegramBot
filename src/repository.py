"""Repository pattern implementation for AMX API data access."""

import pandas as pd
import requests


class AMXRepository:
    """Repository for fetching data from AMX API."""

    BASE_URL = "https://amx.am/api"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://amx.am/",
        "Origin": "https://amx.am",
    }
    TIMEOUT = 20

    def get_instruments(self) -> pd.DataFrame:
        """Fetch instrument data from AMX API."""
        url = f"{self.BASE_URL}/getInstruments"
        response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
        response.raise_for_status()
        data = response.json().get("data", {}).get("instruments", [])
        return pd.DataFrame(data)

    def get_market_data(self, market_type: str = "corporate_bonds") -> pd.DataFrame:
        """Fetch market data from AMX API."""
        url = f"{self.BASE_URL}/getMarketData/{market_type}"
        response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
        response.raise_for_status()
        data = response.json().get("data", [])
        return pd.DataFrame(data)
