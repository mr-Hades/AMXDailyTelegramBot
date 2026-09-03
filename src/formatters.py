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
    def format_for_telegram(cls, bonds: List[Bond], currency: str = "AMD", top_n: int = 25, heading: str = None) -> str:
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
        lines.append(heading or f"🏆 <b>Top {currency} Bonds by Japanese Yield:</b>\n")
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

    @classmethod
    def format_class_split_for_telegram(cls, bonds: List[Bond], currency: str = "AMD", top_n: int = 20) -> List[str]:
        """Format bonds as two Telegram messages: Class A top N, and all other classes top N."""
        a_class_bonds = [b for b in bonds if (b.list_class or "").strip().upper() == "A"]
        other_bonds = [b for b in bonds if (b.list_class or "").strip().upper() != "A"]

        msg_a = cls.format_for_telegram(
            a_class_bonds, currency=currency, top_n=top_n,
            heading=f"🏆 <b>Top {currency} Class A Bonds by Japanese Yield:</b>\n",
        )
        msg_others = cls.format_for_telegram(
            other_bonds, currency=currency, top_n=top_n,
            heading=f"🏆 <b>Top {currency} Other-Class Bonds by Japanese Yield:</b>\n",
        )
        return [msg_a, msg_others]

    @classmethod
    def format_holdings_for_telegram(cls, bonds: List[Bond], currency: str = "AMD") -> str:
        """Format holdings bonds as Telegram message (shows ALL holdings)."""
        today = datetime.now().strftime("%Y-%m-%d")
        emoji = cls.CURRENCY_EMOJI.get(currency, "📊")

        currency_line = f"{emoji}{emoji}{emoji} <b>【 {currency} 】</b> {emoji}{emoji}{emoji}"

        lines = [
            currency_line,
            f"<b>━━━ Our Holdings — Yield Report ━━━</b>",
            f"📅 {today}\n",
        ]
        lines.append(f"📊 <b>{currency} Holdings by Japanese Yield:</b>\n")
        lines.append("<pre>")
        lines.append(f"{'Ticker':<8} {'Mat.':<12} {'Buy Px':>7} {'Price':>7} {'Cpn%':>5} {'Yld%':>6}")
        lines.append("-" * 52)

        count = 0
        unmatched_tickers = []
        for bond in bonds:
            yld = bond.japanese_yield
            price = bond.ask_price
            buy_price = bond.buy_price
            cpn = bond.cpn_rate or 0.0

            if yld is None and price is None:
                # No usable data at all
                if bond.is_unmatched:
                    unmatched_tickers.append(bond.ticker)
                    lines.append(f"⚠️ {bond.ticker}")
                    count += 1
                continue

            buy_price_str = f"{buy_price:>7.2f}" if buy_price is not None else "    N/A"
            price_str = f"{price:>7.2f}" if price is not None else "    N/A"
            cpn_str = f"{cpn:>5.2f}" if cpn is not None else "  N/A"
            yld_str = f"{yld:>6.2f}" if yld is not None else "   N/A"

            ticker = bond.ticker[:8]
            if bond.is_unmatched:
                unmatched_tickers.append(bond.ticker)

            lines.append(
                f"{ticker:<8} {bond.maturity_date:<12} " f"{buy_price_str} {price_str} {cpn_str} " f"{yld_str}"
            )
            count += 1

        lines.append("</pre>")
        lines.append(f"\n📈 Total <b>{currency}</b> holdings: {count}")
        if unmatched_tickers:
            names = ", ".join(unmatched_tickers)
            lines.append(f"⚠️ Not on AMX (sheet values): {names}")

        return "\n".join(lines)

    @staticmethod
    def format_for_console(bonds: List[Bond], top_n: int = 25) -> str:
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
