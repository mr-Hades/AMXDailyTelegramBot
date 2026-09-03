"""Analyzer for bond holdings from Google Sheets."""

from collections import defaultdict
from typing import Dict, List, Optional

from .analyzer import BondAnalyzer
from .holdings_repository import HoldingsRepository
from .models import Bond


class HoldingsAnalyzer:
    """Analyzes Japanese yield for bonds held in a portfolio (Google Sheet)."""

    def __init__(
        self,
        holdings_repository: Optional[HoldingsRepository] = None,
        bond_analyzer: Optional[BondAnalyzer] = None,
    ):
        self.holdings_repo = holdings_repository or HoldingsRepository()
        self.bond_analyzer = bond_analyzer or BondAnalyzer()

    def analyze(self) -> Dict[str, List[Bond]]:
        """Analyze holdings and return bonds grouped by currency.

        Processes every row from the sheet (preserving duplicates).
        Unmatched holdings are included as Bond objects with
        is_unmatched=True so they can be highlighted in reports.

        Returns:
            Dict mapping currency code to list of Bond objects,
            sorted by Japanese yield descending within each currency.
        """
        # Get full row dicts from the sheet (no dedup)
        holding_rows = self.holdings_repo.get_holding_rows()
        if not holding_rows:
            print("⚠️ No holdings found in sheet")
            return {}

        print(f"Found {len(holding_rows)} holdings in sheet")

        id_key = HoldingsRepository._find_id_key(holding_rows[0])
        if not id_key:
            return {}

        # Fetch all instruments from AMX and build lookup tables
        instruments_df = self.bond_analyzer.repository.get_instruments()
        isin_lookup = {}
        ticker_lookup = {}
        for _, row in instruments_df.iterrows():
            isin_val = str(row.get("isin", "")).upper()
            ticker_val = str(row.get("ticker", "")).upper()
            if isin_val:
                isin_lookup[isin_val] = row
            if ticker_val:
                ticker_lookup[ticker_val] = row

        # Process each holding row individually
        result: Dict[str, List[Bond]] = defaultdict(list)
        matched_count = 0
        total = len(holding_rows)

        for idx, row_data in enumerate(holding_rows, 1):
            holding_id = str(row_data.get(id_key, "")).strip()
            hid_upper = holding_id.upper()
            isin_match = isin_lookup.get(hid_upper)
            instrument = isin_match if isin_match is not None else ticker_lookup.get(hid_upper)

            if idx % 5 == 0:
                print(f"  Processing holding {idx}/{total}...")

            if instrument is not None:
                matched_count += 1
                isin = instrument.get("isin")
                currency = instrument.get("currency", "AMD")
                latest_data = self.bond_analyzer.repository.get_latest_market_data_for_instrument(isin)
                bond = self.bond_analyzer._create_bond_from_instrument(instrument, latest_data)
                if bond:
                    bond.buy_price = self._parse_sheet_price(row_data.get("Price"))
                    result[currency].append(bond)
            else:
                # Unmatched — populate from sheet values
                bond = self._bond_from_sheet_row(row_data, id_key)
                currency = str(row_data.get("Currency", "")).strip().upper() or "AMD"
                result[currency].append(bond)

        print(f"Matched {matched_count}/{total} holdings on AMX")

        # Sort each currency group by Japanese yield descending
        for currency in result:
            result[currency].sort(key=lambda b: b.japanese_yield or 0, reverse=True)

        return dict(result)

    @staticmethod
    def _parse_pct(s) -> Optional[float]:
        """Parse '13.00%' → 13.0, return None on failure."""
        s = str(s).strip().replace("%", "")
        try:
            return float(s) if s else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_sheet_price(price) -> Optional[float]:
        """Parse a sheet price cell (handles comma thousand-separators and 'Դ' suffix)."""
        if isinstance(price, str):
            price = price.replace(",", "").replace("Դ", "").strip()
        try:
            return float(price) if price else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _bond_from_sheet_row(row: Dict, id_key: str) -> Bond:
        """Create a Bond from raw sheet data (for unmatched holdings)."""
        ticker = str(row.get(id_key, "")).strip()
        maturity = str(row.get("Maturity Date", "-")).strip() or "-"
        cpn_rate = HoldingsAnalyzer._parse_pct(row.get("Coupon Rate", ""))
        running_yield = HoldingsAnalyzer._parse_pct(row.get("Running Yield", ""))

        # Try numeric price first ("Price Դ" in Bonds sheet),
        # fall back to "Price" (Bonds Daily)
        price = HoldingsAnalyzer._parse_sheet_price(row.get("Price Դ") or row.get("Price"))
        buy_price = HoldingsAnalyzer._parse_sheet_price(row.get("Price"))

        return Bond(
            ticker=ticker,
            isin=ticker,
            maturity_date=maturity,
            ask_price=price,
            buy_price=buy_price,
            cpn_rate=cpn_rate or 0.0,
            japanese_yield=running_yield,
            is_unmatched=True,
        )
