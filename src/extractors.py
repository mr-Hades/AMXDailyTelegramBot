"""Strategy pattern implementations for price and yield extraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PriceExtractor(ABC):
    """Abstract base class for price extraction strategies."""

    @abstractmethod
    def extract(self, price_dict: Dict[str, Any]) -> Optional[float]:
        """Extract price from price dictionary."""
        pass

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value and value != "-":
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return None


class AskPriceExtractor(PriceExtractor):
    """Extract ask price with fallback to avg and close."""

    def extract(self, price_dict: Dict[str, Any]) -> Optional[float]:
        if not isinstance(price_dict, dict):
            return None

        # Primary: ask price
        if result := self._safe_float(price_dict.get("ask")):
            return result

        # Fallback 1: average price
        if result := self._safe_float(price_dict.get("avg")):
            return result

        # Fallback 2: close price
        if result := self._safe_float(price_dict.get("close")):
            return result

        return None


class BidPriceExtractor(PriceExtractor):
    """Extract bid price only (no fallback)."""

    def extract(self, price_dict: Dict[str, Any]) -> Optional[float]:
        if not isinstance(price_dict, dict):
            return None
        return self._safe_float(price_dict.get("bid"))


class YieldExtractor(PriceExtractor):
    """Extract yield with fallback to avg and close."""

    def extract(self, yield_dict: Dict[str, Any]) -> Optional[float]:
        if not isinstance(yield_dict, dict):
            return None

        # Primary: ask yield
        if result := self._safe_float(yield_dict.get("ask")):
            return result

        # Fallback 1: average yield
        if result := self._safe_float(yield_dict.get("avg")):
            return result

        # Fallback 2: close yield
        if result := self._safe_float(yield_dict.get("close")):
            return result

        return None
