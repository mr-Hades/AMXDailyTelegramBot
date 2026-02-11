#!/usr/bin/env python3
"""
AMX Bond Analyzer - Daily bond yield report generator.

Fetches bond data from Armenian Stock Exchange (AMX), calculates Japanese Yield,
and optionally sends reports to Telegram.

Usage:
    python main.py              # Console output only (today's market data)
    python main.py --all        # Include all bonds with historical data
    python main.py --telegram   # Also send to Telegram
    python main.py --all --telegram  # All bonds + send to Telegram
"""

import os
import sys

from src import BondAnalyzer, BondReportFormatter, TelegramNotifier


def main(send_telegram: bool = False, fetch_all: bool = False) -> list:
    """Main entry point."""
    # Initialize components
    analyzer = BondAnalyzer()
    formatter = BondReportFormatter()

    # Analyze AMD bonds
    if fetch_all:
        print("Fetching ALL AMD bonds (using historical data)...")
        print("This may take 1-2 minutes...\n")
        bonds = analyzer.analyze_all(currency="AMD")
    else:
        print("Fetching AMD bonds with today's market data...")
        bonds = analyzer.analyze(currency="AMD")

    # Console output
    print("\nMarket data with Japanese yields (sorted by highest yield):")
    print(formatter.format_for_console(bonds))

    # Statistics
    total_bonds = len(bonds)
    bonds_with_yield = sum(1 for b in bonds if b.japanese_yield is not None)
    bonds_with_price = sum(1 for b in bonds if b.ask_price is not None)
    print(f"\nTotal AMD bonds: {total_bonds}")
    print(f"Bonds with price data: {bonds_with_price}")
    print(f"Bonds with Japanese yield: {bonds_with_yield}")

    # Send to Telegram if configured
    if send_telegram:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)
            message = formatter.format_for_telegram(bonds)
            if notifier.send_message(message):
                print("\n✅ Report sent to Telegram successfully!")
            else:
                print("\n❌ Failed to send report to Telegram")
        else:
            print("\n⚠️ Telegram credentials not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")

    return bonds


if __name__ == "__main__":
    send_to_telegram = "--telegram" in sys.argv
    fetch_all_bonds = "--all" in sys.argv
    main(send_telegram=send_to_telegram, fetch_all=fetch_all_bonds)
