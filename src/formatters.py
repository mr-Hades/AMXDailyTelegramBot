"""Report formatting utilities."""

from datetime import datetime
from typing import List

import pandas as pd

from .models import Bond


class BondReportFormatter:
    """Formats bond data for display/notification."""

    # Currency display settings
    CURRENCY_EMOJI = {
        "AMD": "🇦🇲",
        "USD": "🇺🇸",
        "EUR": "🇪🇺",
    }

    @classmethod
    def format_for_telegram(cls, bonds: List[Bond], currency: str = "AMD", top_n: int = 15) -> str:
        """Format top bonds as Telegram message."""
        today = datetime.now().strftime("%Y-%m-%d")
        emoji = cls.CURRENCY_EMOJI.get(currency, "📊")
        
        # Create aggressive currency header
        currency_line = f"{emoji}{emoji}{emoji} <b>【 {currency} 】</b> {emoji}{emoji}{emoji}"
        
        lines = [
            currency_line,
            f"<b>━━━━━ AMX Bond Yields Report ━━━━━</b>",
            f"📅 {today}\n",
        ]
        lines.append(f"🏆 <b>Top {currency} Bonds by Japanese Yield:</b>\n")
        lines.append("<pre>")
        lines.append(f"{'Ticker':<8} {'Mat.':<12} {'Price':>7} {'Cpn%':>5} {'Yld%':>6} {'Cls':>3}")
        lines.append("-" * 47)

        for bond in bonds[:top_n]:
            if bond.japanese_yield is not None:
                lc = bond.list_class or "-"
                lines.append(
                    f"{bond.ticker:<8} {bond.maturity_date:<12} "
                    f"{bond.ask_price:>7.2f} {bond.cpn_rate:>5.2f} "
                    f"{bond.japanese_yield:>6.2f} {lc:>3}"
                )
        lines.append("</pre>")
        lines.append(f"\n📈 Total <b>{currency}</b> bonds analyzed: {len(bonds)}")

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
            "list_class",
        ]
        return df[display_columns].head(top_n).to_string()
