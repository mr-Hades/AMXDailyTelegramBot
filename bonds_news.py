#!/usr/bin/env python3
"""
CBA Prospectus Monitor — Detects new bond Program Prospectus registrations
from CBA chairman decisions and tracks them until listed on AMX.

Usage:
    python bonds_news.py                # Console output only
    python bonds_news.py --telegram     # Also send alerts to Telegram
    python bonds_news.py --status       # Show active tracker status
    python bonds_news.py --reset        # Reset state (re-scan all)
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

from src.news_formatter import ProspectusFormatter
from src.news_models import ProspectusDecision
from src.news_scraper import CBAProspectusScraper
from src.notifier import TelegramNotifier

STATE_FILE = Path(__file__).parent / "prospectus_state.json"

# AMX API for cross-referencing listings
AMX_API_URL = "https://amx.am/api/getInstruments"
AMX_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://amx.am/",
    "Origin": "https://amx.am",
}


def load_state() -> Dict:
    """Load persisted state from JSON file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"known_ids": [], "active": {}, "dismissed": []}


def save_state(state: Dict) -> None:
    """Persist state to JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# Words to strip when normalizing company names for matching
_LEGAL_SUFFIXES = re.compile(
    r"\b(cjsc|ojsc|llc|uco|rco|cc|jsc|ltd|inc|co|closed|open|joint[- ]?stock|company|"
    r"universal|credit|organization)\b",
    re.I,
)
_STRIP_CHARS = re.compile(r"[\"'\u00ab\u00bb\u201c\u201d\u2018\u2019\u2013\u2014,.\-]+")


def _normalize_name(name: str) -> str:
    """Normalize company name for comparison."""
    name = _STRIP_CHARS.sub(" ", name.lower())
    name = _LEGAL_SUFFIXES.sub(" ", name)
    return " ".join(name.split()).strip()


def fetch_amx_issuers() -> List[Tuple[str, str, str]]:
    """Fetch current AMX instruments. Returns [(raw_name, normalized_name, isin)]."""
    try:
        resp = requests.get(AMX_API_URL, headers=AMX_HEADERS, timeout=20)
        resp.raise_for_status()
        instruments = resp.json().get("data", {}).get("instruments", [])
        seen: Set[str] = set()
        result: List[Tuple[str, str, str]] = []
        for inst in instruments:
            raw = (inst.get("issuer_name_en") or "").strip()
            isin = inst.get("isin", "")
            key = raw.lower()
            if raw and isin and key not in seen:
                seen.add(key)
                result.append((raw, _normalize_name(raw), isin))
        return result
    except requests.RequestException as e:
        print(f"AMX fetch error: {e}")
        return []


def check_amx_listing(
    company_name: str, amx_issuers: List[Tuple[str, str, str]]
) -> Optional[str]:
    """Check if a company is listed on AMX. Returns ISIN if found."""
    target = _normalize_name(company_name)
    if not target:
        return None

    target_nospace = target.replace(" ", "")

    for raw, norm, isin in amx_issuers:
        # Exact normalized match
        if target == norm:
            return isin

        # One name fully contains the other
        if target in norm or norm in target:
            return isin

        # Space-insensitive match (IDBank vs ID Bank, ArmEconomBank vs Armeconombank)
        norm_nospace = norm.replace(" ", "")
        if target_nospace == norm_nospace:
            return isin
        if target_nospace in norm_nospace or norm_nospace in target_nospace:
            return isin

    return None


def run(send_telegram: bool = False, show_status: bool = False) -> None:
    """Main monitoring run."""
    state = load_state()
    known_ids: Set[str] = set(state.get("known_ids", []))
    active: Dict[str, dict] = state.get("active", {})
    dismissed: Set[str] = set(state.get("dismissed", []))

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

    # Add new decisions to active tracker
    for d in new_decisions:
        known_ids.add(d.decision_id)
        active[d.decision_id] = {
            "decision_id": d.decision_id,
            "date": d.date,
            "title": d.title,
            "company_name": d.company_name,
            "url": d.url,
            "is_supplement": d.is_supplement,
            "amx_listed": False,
            "amx_isin": None,
        }

    # --- Check AMX for listings of active companies ---
    active_decisions: List[ProspectusDecision] = []
    newly_listed: List[ProspectusDecision] = []

    if active:
        print("Checking AMX for listings of active companies...")
        amx_issuers = fetch_amx_issuers()
        print(f"AMX has {len(amx_issuers)} unique issuers")

        for did, info in list(active.items()):
            if info.get("amx_listed") or did in dismissed:
                continue

            # Auto-dismiss decisions older than 1 year
            try:
                decision_date = datetime.strptime(info["date"], "%Y-%m-%d")
                if datetime.now() - decision_date > timedelta(days=365):
                    dismissed.add(did)
                    print(f"  ⏭️  {info['company_name']} ({info['date']}) — auto-dismissed (>1 year old)")
                    continue
            except (ValueError, KeyError):
                pass

            decision = ProspectusDecision(
                decision_id=info["decision_id"],
                date=info["date"],
                title=info["title"],
                company_name=info["company_name"],
                url=info["url"],
                is_supplement=info.get("is_supplement", False),
            )

            isin = check_amx_listing(info["company_name"], amx_issuers)
            if isin:
                decision.amx_listed = True
                decision.amx_isin = isin
                info["amx_listed"] = True
                info["amx_isin"] = isin
                newly_listed.append(decision)
                print(f"  ✅ {info['company_name']} → listed (ISIN: {isin})")
            else:
                active_decisions.append(decision)
                print(f"  ⏳ {info['company_name']} → not yet listed")

    # --- Console output ---
    print(f"\n{'='*50}")
    print(f"New decisions: {len(new_decisions)}")
    print(f"Newly listed on AMX: {len(newly_listed)}")
    print(f"Still active (pending): {len(active_decisions)}")
    print(f"Total tracked: {len(known_ids)}")
    print(f"{'='*50}")

    if new_decisions:
        print("\n📄 New Prospectus Registrations:")
        for d in new_decisions:
            tag = "📎 Supplement" if d.is_supplement else "📄 New"
            print(f"  {tag}: {d.company_name} ({d.date})")

    if active_decisions:
        print("\n⏳ Active (pending AMX listing):")
        for d in active_decisions:
            print(f"  - {d.company_name} ({d.date})")

    # --- Telegram notifications ---
    if send_telegram:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if bot_token and chat_id:
            notifier = TelegramNotifier(bot_token, chat_id)

            if first_run:
                # First run: only send active tracker, skip flooding with history
                print("First run — skipping individual notifications for historical data")
                msg, buttons = formatter.format_active_tracker(active_decisions)
                if buttons:
                    if notifier.send_message_with_buttons(msg, buttons):
                        print("✅ Active tracker sent to Telegram (with remove buttons)")
                    else:
                        print("❌ Failed to send active tracker")
                elif msg:
                    if notifier.send_message(msg):
                        print("✅ Active tracker sent to Telegram")
                    else:
                        print("❌ Failed to send active tracker")
            else:
                # Subsequent runs: notify about new decisions and status changes
                if new_decisions:
                    msgs = formatter.format_new_decisions(new_decisions)
                    for msg in msgs:
                        if notifier.send_message(msg):
                            print("✅ New decision alert sent to Telegram")
                        else:
                            print("❌ Failed to send new decision alert")
                        time.sleep(1)

                # Notify about newly listed
                for d in newly_listed:
                    msg = formatter.format_listed_notification(d)
                    if notifier.send_message(msg):
                        print(f"✅ Listed notification sent for {d.company_name}")
                    else:
                        print(f"❌ Failed to send listed notification for {d.company_name}")
                    time.sleep(1)

                # Send active tracker with remove buttons
                if show_status or new_decisions:
                    msg, buttons = formatter.format_active_tracker(active_decisions)
                    if buttons:
                        if notifier.send_message_with_buttons(msg, buttons):
                            print("✅ Active tracker sent to Telegram (with remove buttons)")
                        else:
                            print("❌ Failed to send active tracker")
                    else:
                        if notifier.send_message(msg):
                            print("✅ Active tracker sent to Telegram")
                        else:
                            print("❌ Failed to send active tracker")
        else:
            print("\n⚠️ Telegram credentials not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")

    elif show_status and active_decisions:
        msg, _ = formatter.format_active_tracker(active_decisions)
        print("\n" + msg)

    # --- Save state ---
    state["known_ids"] = sorted(known_ids)
    state["active"] = active
    state["dismissed"] = sorted(dismissed)
    save_state(state)
    print(f"\nState saved to {STATE_FILE}")


def reset_state() -> None:
    """Reset the state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("State reset. Next run will scan all decisions.")
    else:
        print("No state file found.")


def poll_callbacks() -> None:
    """One-shot: process any pending dismiss callbacks and exit."""
    _process_callbacks(once=True)


def listen_for_callbacks() -> None:
    """Run continuously, responding to dismiss button presses instantly."""
    _process_callbacks(once=False)


def _rebuild_active_tracker(
    active: Dict[str, dict], dismissed: Set[str]
) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Rebuild the active tracker message from state data.

    Converts the active dict entries (minus dismissed) into
    ProspectusDecision objects and formats them.
    """
    from src.news_formatter import ProspectusFormatter

    remaining = [
        ProspectusDecision(
            decision_id=did,
            date=info.get("date", ""),
            title=info.get("title", ""),
            company_name=info.get("company_name", ""),
            url=info.get("url", ""),
            preview=info.get("preview", ""),
            is_supplement=info.get("is_supplement", False),
        )
        for did, info in active.items()
        if did not in dismissed and not info.get("amx_listed", False)
    ]
    return ProspectusFormatter.format_active_tracker(remaining)


def _process_callbacks(once: bool = False) -> None:
    """Core callback processor.

    Args:
        once: If True, fetch once and exit. If False, loop forever (long-poll).
    """
    from src.news_formatter import DISMISS_PREFIX

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials not configured")
        return

    notifier = TelegramNotifier(bot_token, chat_id)
    state = load_state()
    offset: Optional[int] = state.get("last_update_id")
    if offset is not None:
        offset += 1

    if not once:
        print("🔔 Listening for button presses... (Ctrl+C to stop)")

    try:
        while True:
            timeout = 1 if once else 30
            updates = notifier.get_updates(offset=offset, timeout=timeout)

            for update in updates:
                offset = update["update_id"] + 1
                cb = update.get("callback_query")
                if not cb:
                    continue

                data = cb.get("data", "")
                if not data.startswith(DISMISS_PREFIX):
                    continue

                # Only allow chat admins to dismiss
                user_id = cb.get("from", {}).get("id")
                if not user_id or not notifier.is_chat_admin(user_id):
                    notifier.answer_callback_query(
                        cb["id"], text="⛔ Only admins can remove companies"
                    )
                    continue

                # Reload state in case it changed between iterations
                state = load_state()
                dismissed: Set[str] = set(state.get("dismissed", []))
                active: Dict[str, dict] = state.get("active", {})

                decision_id = data[len(DISMISS_PREFIX):]
                info = active.get(decision_id)
                company = info["company_name"] if info else decision_id
                date = info["date"] if info else "?"

                dismissed.add(decision_id)

                # Save immediately so the dismiss is persisted
                state["last_update_id"] = update["update_id"]
                state["dismissed"] = sorted(dismissed)
                save_state(state)

                notifier.answer_callback_query(
                    cb["id"], text=f"✅ Removed {company} ({date})"
                )
                print(f"  Dismissed: {company} ({date}) [ID={decision_id}]")

                # Edit the original message to remove the dismissed entry
                msg_obj = cb.get("message", {})
                message_id = msg_obj.get("message_id")
                msg_chat_id = str(msg_obj.get("chat", {}).get("id", ""))
                if message_id:
                    new_text, new_buttons = _rebuild_active_tracker(
                        active, dismissed
                    )
                    notifier.edit_message_with_buttons(
                        message_id, new_text, new_buttons, chat_id=msg_chat_id
                    )

            # Persist offset even if no dismiss happened
            if updates:
                state = load_state()
                state["last_update_id"] = (offset - 1) if offset else None
                save_state(state)

            if once:
                break

    except KeyboardInterrupt:
        print("\n🛑 Listener stopped.")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_state()
    elif "--listen" in sys.argv:
        listen_for_callbacks()
    elif "--poll" in sys.argv:
        poll_callbacks()
    else:
        run(
            send_telegram="--telegram" in sys.argv,
            show_status="--status" in sys.argv,
        )
