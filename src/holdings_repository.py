"""Repository for reading bond holdings from Google Sheets."""

import os
from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials


class HoldingsRepository:
    """Reads bond holdings from a Google Sheet."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        sheet_name: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
        self.spreadsheet_id = spreadsheet_id or os.environ.get("HOLDINGS_SPREADSHEET_ID", "")
        self.sheet_name = sheet_name or os.environ.get("HOLDINGS_SHEET_NAME", "Bonds")
        self._client = None

    def _get_client(self):
        """Lazily create and cache the gspread client."""
        if self._client is None:
            credentials = Credentials.from_service_account_file(self.credentials_path, scopes=self.SCOPES)
            self._client = gspread.authorize(credentials)
        return self._client

    def get_holdings(self) -> List[Dict]:
        """Read all rows from the holdings sheet.

        Returns list of dicts (one per row) with column headers as keys.
        """
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(self.sheet_name)
        return worksheet.get_all_records()

    def get_holding_rows(self) -> List[Dict]:
        """Get all holding rows from the sheet as full dicts.

        Returns one dict per row (preserving duplicates and order).
        """
        records = self.get_holdings()
        if not records:
            return []

        id_key = self._find_id_key(records[0] if records else {})
        if not id_key:
            return []

        return [r for r in records if str(r.get(id_key, "")).strip()]

    @staticmethod
    def _find_id_key(sample: Dict) -> Optional[str]:
        """Find the ISIN or Ticker column name (case-insensitive)."""
        for key in sample:
            if key.strip().upper() == "ISIN":
                return key
        for key in sample:
            if key.strip().upper() == "TICKER":
                return key
        print("⚠️ No ISIN or Ticker column found in holdings sheet")
        return None

    def update_daily_prices(self, price_map: Dict[str, float]) -> None:
        """Update the Price column in the 'Bonds Daily' sheet.

        Args:
            price_map: Dict of ISIN/ticker (uppercase) → ask_price.
        """
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet("Bonds Daily")

        all_values = worksheet.get_all_values()
        if not all_values:
            print("⚠️ Bonds Daily sheet is empty")
            return

        headers = all_values[0]
        isin_col = None
        price_col = None
        for i, h in enumerate(headers):
            upper = h.strip().upper()
            if upper == "ISIN":
                isin_col = i
            elif upper == "PRICE":
                price_col = i

        if isin_col is None or price_col is None:
            print("⚠️ Could not find ISIN or Price column in Bonds Daily")
            return

        # Build batch updates — skip header (row 1)
        updates = []
        for row_idx, row in enumerate(all_values[1:], start=2):
            isin_val = row[isin_col].strip().upper() if isin_col < len(row) else ""
            if not isin_val or isin_val == "-":
                continue
            price = price_map.get(isin_val)
            if price is not None:
                cell = gspread.utils.rowcol_to_a1(row_idx, price_col + 1)
                updates.append({"range": cell, "values": [[price]]})

        if updates:
            worksheet.batch_update(updates)
            print(f"✅ Updated {len(updates)} prices in Bonds Daily sheet")
        else:
            print("⚠️ No prices to update in Bonds Daily")
