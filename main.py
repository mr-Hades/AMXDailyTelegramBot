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
from typing import Dict, List

from src import BondAnalyzer, BondReportFormatter, TelegramNotifier
from src.models import Bond

# Supported currencies
SUPPORTED_CURRENCIES = ["AMD", "USD", "EUR"]


def analyze_currency(analyzer: BondAnalyzer, formatter: BondReportFormatter, 
                     currency: str, fetch_all: bool = False) -> List[Bond]:
    """Analyze bonds for a specific currency."""
    if fetch_all:
        print(f"Fetching ALL {currency} bonds (using historical data)...")
        bonds = analyzer.analyze_all(currency=currency)
    else:
        print(f"Fetching {currency} bonds with today's market data...")
        bonds = analyzer.analyze(currency=currency)

    # Console output
    print(f"\n{currency} Market data with Japanese yields (sorted by highest yield):")
    print(formatter.format_for_console(bonds))

    # Statistics
    total_bonds = len(bonds)
    bonds_with_yield = sum(1 for b in bonds if b.japanese_yield is not None)
    bonds_with_price = sum(1 for b in bonds if b.ask_price is not None)
    print(f"\nTotal {currency} bonds: {total_bonds}")
    print(f"Bonds with price data: {bonds_with_price}")
    print(f"Bonds with Japanese yield: {bonds_with_yield}")
    
    return bonds


def main(send_telegram: bool = False, fetch_all: bool = False) -> Dict[str, List[Bond]]:
    """Main entry point."""
    # Initialize components
    analyzer = BondAnalyzer()
    formatter = BondReportFormatter()
    
    if fetch_all:
        print("This may take a few minutes...\n")

    # Analyze bonds for all supported currencies
    all_bonds: Dict[str, List[Bond]] = {}
    
    for currency in SUPPORTED_CURRENCIES:
        print(f"\n{'='*50}")
        print(f"Processing {currency} bonds...")
        print('='*50)
        bonds = analyze_currency(analyzer, formatter, currency, fetch_all)
        all_bonds[currency] = bonds

    # Send to Telegram if configured
    if send_telegram:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)
            
            # Send separate message for each currency
            for currency in SUPPORTED_CURRENCIES:
                bonds = all_bonds[currency]
                if bonds:  # Only send if there are bonds
                    message = formatter.format_for_telegram(bonds, currency=currency)
                    if notifier.send_message(message):
                        print(f"\n✅ {currency} report sent to Telegram successfully!")
                    else:
                        print(f"\n❌ Failed to send {currency} report to Telegram")
                else:
                    print(f"\n⚠️ No {currency} bonds to report")
        else:
            print("\n⚠️ Telegram credentials not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")

    return all_bonds


if __name__ == "__main__":
    send_to_telegram = "--telegram" in sys.argv
    fetch_all_bonds = "--all" in sys.argv
    main(send_telegram=send_to_telegram, fetch_all=fetch_all_bonds)
