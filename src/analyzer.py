"""Bond analyzer - main facade for the application."""

from typing import Any, Dict, List, Optional

import pandas as pd

from .calculators import CouponParser, JapaneseYieldCalculator
from .extractors import AskPriceExtractor, BidPriceExtractor, YieldExtractor
from .models import Bond
from .repository import AMXRepository


class BondAnalyzer:
    """
    Main service for analyzing bonds.
    Acts as a facade to coordinate all components.
    """

    def __init__(
        self,
        repository: Optional[AMXRepository] = None,
        yield_calculator: Optional[JapaneseYieldCalculator] = None,
    ):
        self.repository = repository or AMXRepository()
        self.yield_calculator = yield_calculator or JapaneseYieldCalculator()
        self.ask_price_extractor = AskPriceExtractor()
        self.bid_price_extractor = BidPriceExtractor()
        self.yield_extractor = YieldExtractor()
        self.coupon_parser = CouponParser()

    def analyze(self, currency: str = "AMD") -> List[Bond]:
        """
        Analyze bonds for the given currency.
        Returns list of Bond objects sorted by Japanese yield (descending).
        """
        # Fetch data
        instruments_df = self.repository.get_instruments()
        market_df = self.repository.get_market_data()

        # Filter by currency
        instruments_df = instruments_df.query(f"currency == '{currency}'")
        market_df = market_df.query(f"cur == '{currency}'")

        # Create instrument lookup
        instruments_lookup = instruments_df.set_index("isin").to_dict("index")

        # Process bonds
        bonds = []
        for _, row in market_df.iterrows():
            bond = self._create_bond(row, instruments_lookup)
            if bond:
                bonds.append(bond)

        # Sort by Japanese yield (descending)
        bonds.sort(key=lambda b: b.japanese_yield or 0, reverse=True)

        return bonds

    def analyze_all(self, currency: str = "AMD", show_progress: bool = True) -> List[Bond]:
        """
        Analyze ALL bonds for the given currency using historical data.
        This provides consistent bond counts by fetching each instrument's latest data.

        Note: This is slower as it makes one API call per bond, but ensures
        all bonds are included regardless of daily market activity.

        Args:
            currency: Currency to filter by (default: AMD)
            show_progress: Whether to print progress updates

        Returns:
            List of Bond objects sorted by Japanese yield (descending)
        """
        instruments_df = self.repository.get_instruments()
        instruments_df = instruments_df.query(f"currency == '{currency}'")

        total = len(instruments_df)
        bonds = []

        for idx, (_, instrument) in enumerate(instruments_df.iterrows(), 1):
            isin = instrument.get("isin")
            if not isin:
                continue

            if show_progress and idx % 10 == 0:
                print(f"  Processing {idx}/{total} instruments...")

            # Get latest market data for this instrument
            latest_data = self.repository.get_latest_market_data_for_instrument(isin)

            # Create bond from instrument + latest market data
            bond = self._create_bond_from_instrument(instrument, latest_data)
            if bond:
                bonds.append(bond)

        # Sort by Japanese yield (descending)
        bonds.sort(key=lambda b: b.japanese_yield or 0, reverse=True)

        return bonds

    def _create_bond_from_instrument(self, instrument: pd.Series, market_data: Optional[Dict]) -> Optional[Bond]:
        """Create a Bond object from instrument data and optional market data."""
        cpn_rate = self.coupon_parser.parse_rate(instrument.get("cpn_rate"))
        par_value = self._parse_par_value(instrument.get("per_value"))

        # Extract prices from market data if available
        ask_price = None
        bid_price = None
        ask_yield = None

        if market_data:
            ask_price = self._safe_float(market_data.get("best_ask_price"))
            bid_price = self._safe_float(market_data.get("best_bid_price"))
            ask_yield = self._safe_float(market_data.get("best_ask_yield"))

            # Fallback to avg/close prices if no bid/ask
            if ask_price is None:
                ask_price = self._safe_float(market_data.get("avg_price")) or self._safe_float(
                    market_data.get("close_price")
                )
            if ask_yield is None:
                ask_yield = self._safe_float(market_data.get("avg_yield")) or self._safe_float(
                    market_data.get("close_yield")
                )

        bond = Bond(
            ticker=instrument.get("ticker", ""),
            isin=instrument.get("isin", ""),
            maturity_date=instrument.get("maturity_date", ""),
            short_name=instrument.get("short_name_en"),
            ask_price=ask_price,
            bid_price=bid_price,
            ask_yield=ask_yield,
            cpn_rate=cpn_rate,
            cpn_frequency=instrument.get("cpn_frequency_en"),
            par_value=par_value,
        )

        # Calculate Japanese yield
        bond.japanese_yield = self.yield_calculator.calculate(bond)

        return bond

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == "" or value == "-":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _create_bond(self, row: pd.Series, instruments_lookup: Dict) -> Optional[Bond]:
        """Create a Bond object from market data row."""
        isin = row.get("isin")
        instrument = instruments_lookup.get(isin, {})

        # Parse values
        cpn_rate = self.coupon_parser.parse_rate(instrument.get("cpn_rate"))
        par_value = self._parse_par_value(instrument.get("per_value"))

        bond = Bond(
            ticker=row.get("ticker", ""),
            isin=isin or "",
            maturity_date=row.get("maturity_date", ""),
            short_name=row.get("short_name_en"),
            ask_price=self.ask_price_extractor.extract(row.get("price", {})),
            bid_price=self.bid_price_extractor.extract(row.get("price", {})),
            ask_yield=self.yield_extractor.extract(row.get("yield", {})),
            cpn_rate=cpn_rate,
            cpn_frequency=instrument.get("cpn_frequency_en"),
            par_value=par_value,
        )

        # Calculate Japanese yield
        bond.japanese_yield = self.yield_calculator.calculate(bond)

        return bond

    def _parse_par_value(self, value: Any) -> Optional[float]:
        """Parse par value to float."""
        if not value:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (ValueError, TypeError):
            return None

    def to_dataframe(self, bonds: List[Bond]) -> pd.DataFrame:
        """Convert list of bonds to pandas DataFrame."""
        return pd.DataFrame([vars(b) for b in bonds])
