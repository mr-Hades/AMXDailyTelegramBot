"""Repository pattern implementation for AMX API data access."""

from typing import Any, Dict, List, Optional

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

    def get_instrument_detail(self, isin: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed instrument data including historical market data."""
        url = f"{self.BASE_URL}/getInstrument/{isin}"
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json().get("data", {})
        except requests.RequestException:
            return None

    def get_latest_market_data_for_instrument(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent market data for a specific instrument.
        Returns the latest entry from the instrument's market_data history.
        """
        detail = self.get_instrument_detail(isin)
        if not detail:
            return None

        market_data = detail.get("market_data", [])
        if not market_data:
            return None

        # Sort by order_date descending and return the latest
        sorted_data = sorted(market_data, key=lambda x: x.get("order_date", ""), reverse=True)
        return sorted_data[0] if sorted_data else None

    def get_all_instruments_with_latest_data(self, currency: str = "AMD") -> List[Dict[str, Any]]:
        """
        Fetch all instruments for a currency with their latest market data.
        This provides consistent bond counts by using instruments as the base.
        """
        instruments_df = self.get_instruments()
        instruments_df = instruments_df.query(f"currency == '{currency}'")

        results = []
        for _, instrument in instruments_df.iterrows():
            isin = instrument.get("isin")
            if not isin:
                continue

            # Get latest market data for this instrument
            latest_data = self.get_latest_market_data_for_instrument(isin)

            results.append({"instrument": instrument.to_dict(), "latest_market_data": latest_data})

        return results
