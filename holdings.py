#!/usr/bin/env python3
"""
Holdings Yield Report — Daily Japanese yield for our bond portfolio.

Reads holdings from a Google Sheet, fetches current market data from AMX,
calculates Japanese Yield, and optionally sends to a Telegram channel.

Usage:
    python holdings.py              # Console output only
    python holdings.py --telegram   # Also send to Telegram
"""

import os
import sys

from src import BondReportFormatter, TelegramNotifier
from src.holdings_analyzer import HoldingsAnalyzer


def main(send_telegram: bool = False) -> None:
    """Main entry point."""
    formatter = BondReportFormatter()
    analyzer = HoldingsAnalyzer()

    print("Analyzing holdings from Google Sheet...")
    holdings_by_currency = analyzer.analyze()

    if not holdings_by_currency:
        print("No holdings found or matched.")
        return

    currencies = list(holdings_by_currency.keys())

    # Console output
    for currency in currencies:
        bonds = holdings_by_currency[currency]
        print(f"\n{'='*50}")
        print(f"{currency} Holdings — Japanese Yield")
        print("=" * 50)
        matched_bonds = [b for b in bonds if not b.is_unmatched]
        unmatched_bonds = [b for b in bonds if b.is_unmatched]
        if matched_bonds:
            print(formatter.format_for_console(matched_bonds, top_n=len(matched_bonds)))

        bonds_with_yield = sum(1 for b in matched_bonds if b.japanese_yield is not None)
        print(f"\nTotal {currency} holdings: {len(matched_bonds)}")
        print(f"Holdings with Japanese yield: {bonds_with_yield}")

        if unmatched_bonds:
            print(f"\n⚠️ {len(unmatched_bonds)} holding(s) not on AMX (sheet values):")
            for b in unmatched_bonds:
                yld = f"{b.japanese_yield:.2f}%" if b.japanese_yield else "N/A"
                price = f"{b.ask_price:.2f}" if b.ask_price else "N/A"
                cpn = f"{b.cpn_rate:.2f}%" if b.cpn_rate else "N/A"
                print(f"  ⚠️ {b.ticker}  Mat: {b.maturity_date}  Price: {price}  Cpn: {cpn}  Yld: {yld}")

    # Send to Telegram
    if send_telegram:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_HOLDINGS_CHAT_ID")

        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)

            for currency in currencies:
                bonds = holdings_by_currency[currency]
                if bonds:
                    message = formatter.format_holdings_for_telegram(bonds, currency=currency)
                    if notifier.send_message(message):
                        print(f"\n✅ {currency} holdings report sent to Telegram!")
                    else:
                        print(f"\n❌ Failed to send {currency} holdings report")
                else:
                    print(f"\n⚠️ No {currency} holdings to report")
        else:
            print("\n⚠️ Telegram credentials not configured")
            print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_HOLDINGS_CHAT_ID")

    # Update prices in Bonds Daily sheet
    price_map = {}
    for bonds in holdings_by_currency.values():
        for bond in bonds:
            if not bond.is_unmatched and bond.ask_price is not None:
                price_map[bond.ticker.upper()] = bond.ask_price
                price_map[bond.isin.upper()] = bond.ask_price

    if price_map:
        print("\nUpdating prices in Bonds Daily sheet...")
        analyzer.holdings_repo.update_daily_prices(price_map)


if __name__ == "__main__":
    send_to_telegram = "--telegram" in sys.argv
    main(send_telegram=send_to_telegram)
