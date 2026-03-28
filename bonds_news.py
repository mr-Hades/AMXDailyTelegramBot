#!/usr/bin/env python3
"""
CBA Prospectus Monitor — Detects new bond Program Prospectus registrations
from CBA chairman decisions and sends Telegram notifications.

Usage:
    python bonds_news.py                # Console output only
    python bonds_news.py --telegram     # Also send alerts to Telegram
    python bonds_news.py --reset        # Reset state (re-scan all)
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Set

from src.news_formatter import ProspectusFormatter
from src.news_scraper import CBAProspectusScraper
from src.notifier import TelegramNotifier

STATE_FILE = Path(__file__).parent / "prospectus_state.json"


def load_state() -> Dict:
    """Load persisted state from JSON file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"known_ids": []}


def save_state(state: Dict) -> None:
    """Persist state to JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def run(send_telegram: bool = False) -> None:
    """Main monitoring run."""
    state = load_state()
    known_ids: Set[str] = set(state.get("known_ids", []))

    scraper = CBAProspectusScraper()
    formatter = ProspectusFormatter()

    # --- Fetch new decisions ---
    first_run = not known_ids
    if known_ids:
        print("Checking for new prospectus decisions...")
        new_decisions = scraper.fetch_latest_decisions(known_ids)
    else:
        print("First run — scanning all prospectus decisions...")
        new_decisions = scraper.fetch_decisions(max_pages=5)

    print(f"Found {len(new_decisions)} new decision(s)")

    # Register all fetched IDs so we don't notify about them again
    for d in new_decisions:
        known_ids.add(d.decision_id)

    # --- Console output ---
    print(f"\n{'='*50}")
    print(f"New decisions: {len(new_decisions)}")
    print(f"Total tracked: {len(known_ids)}")
    print(f"{'='*50}")

    if new_decisions:
        print("\n📄 New Prospectus Registrations:")
        for d in new_decisions:
            tag = "📎 Supplement" if d.is_supplement else "📄 New"
            print(f"  {tag}: {d.company_name} ({d.date})")

    # --- Telegram notifications ---
    if send_telegram and new_decisions and not first_run:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)
            msgs = formatter.format_new_decisions(new_decisions)
            for msg in msgs:
                if notifier.send_message(msg):
                    print("✅ New decision alert sent to Telegram")
                else:
                    print("❌ Failed to send new decision alert")
                time.sleep(1)
        else:
            print("\n⚠️ Telegram credentials not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
    elif first_run:
        print("First run — skipping notifications for historical data")

    # --- Save state ---
    state["known_ids"] = sorted(known_ids)
    save_state(state)
    print(f"\nState saved to {STATE_FILE}")


def reset_state() -> None:
    """Reset the state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("State reset. Next run will scan all decisions.")
    else:
        print("No state file found.")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_state()
    else:
        run(send_telegram="--telegram" in sys.argv)
