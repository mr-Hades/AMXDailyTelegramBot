"""Report formatting utilities."""

from datetime import datetime
from typing import List

import pandas as pd

from .models import Bond


class BondReportFormatter:
    """Formats bond data for display/notification."""

    @staticmethod
    def format_for_telegram(bonds: List[Bond], top_n: int = 15) -> str:
        """Format top bonds as Telegram message."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"📊 <b>AMX Bond Yields Report</b>", f"📅 {today}\n"]
        lines.append("<b>Top Bonds by Japanese Yield:</b>\n")
        lines.append("<pre>")
        lines.append(f"{'Ticker':<8} {'Maturity':<12} {'Price':>7} {'Cpn%':>5} {'Yield%':>6}")
        lines.append("-" * 45)

        for bond in bonds[:top_n]:
            if bond.japanese_yield is not None:
                lines.append(
                    f"{bond.ticker:<8} {bond.maturity_date:<12} "
                    f"{bond.ask_price:>7.2f} {bond.cpn_rate:>5.2f} "
                    f"{bond.japanese_yield:>6.2f}"
                )
        lines.append("</pre>")
        lines.append(f"\n📈 Total AMD bonds analyzed: {len(bonds)}")

        return "\n".join(lines)

    @staticmethod
    def format_for_console(bonds: List[Bond], top_n: int = 15) -> str:
        """Format bonds for console output."""
        df = pd.DataFrame([vars(b) for b in bonds])
        display_columns = [
            "ticker",
            "maturity_date",
            "ask_price",
            "cpn_rate",
            "cpn_frequency",
            "japanese_yield",
        ]
        return df[display_columns].head(top_n).to_string()
