"""Telegram message formatting for prospectus notifications."""

from typing import Dict, List, Tuple

from .news_models import ProspectusDecision

# Callback data prefix for dismiss buttons
DISMISS_PREFIX = "dismiss:"

# Max decisions per message to stay under Telegram's 4096-char limit
_BATCH_SIZE = 8


class ProspectusFormatter:
    """Formats prospectus decision data for Telegram messages."""

    @staticmethod
    def format_new_decisions(decisions: List[ProspectusDecision]) -> List[str]:
        """Format newly detected prospectus decisions as Telegram alerts.

        Returns a list of messages (batched to stay under the char limit).
        """
        if not decisions:
            return []

        messages: List[str] = []
        for i in range(0, len(decisions), _BATCH_SIZE):
            batch = decisions[i : i + _BATCH_SIZE]
            part = f" ({i // _BATCH_SIZE + 1})" if len(decisions) > _BATCH_SIZE else ""
            lines = [
                f"🔔 <b>New Bond Prospectus Registration{part}</b>",
                "",
            ]
            for d in batch:
                tag = "📎 Supplement" if d.is_supplement else "📄 New Prospectus"
                lines.append(f"{tag}: <b>{d.company_name}</b>")
                lines.append(f"   📅 Prospectus date: {d.date}")
                lines.append(f'   📝 <a href="{d.url}">{d.title[:100]}</a>')
                lines.append("")

            if i + _BATCH_SIZE >= len(decisions):
                lines.append(
                    "⏳ <i>These companies are expected to place bonds soon. " "Monitoring AMX for listing.</i>"
                )

            messages.append("\n".join(lines))

        return messages

    @staticmethod
    def format_active_tracker(
        active: List[ProspectusDecision],
    ) -> Tuple[str, List[List[Dict[str, str]]]]:
        """Format active prospectuses with remove buttons.

        Returns:
            (message_text, inline_keyboard_rows)
        """
        if not active:
            return (
                "✅ No active prospectus registrations pending AMX listing.",
                [],
            )

        sorted_active = sorted(active, key=lambda x: x.date, reverse=True)

        lines = [
            "📋 <b>Active Prospectus Registrations</b>",
            "<i>(Pending AMX listing)</i>",
            "",
        ]

        buttons: List[List[Dict[str, str]]] = []
        for d in sorted_active:
            tag = "📎" if d.is_supplement else "📄"
            lines.append(f"{tag} <b>{d.company_name}</b> — {d.date}")
            buttons.append(
                [
                    {
                        "text": f"❌ {d.company_name} ({d.date})",
                        "callback_data": f"{DISMISS_PREFIX}{d.decision_id}",
                    }
                ]
            )

        lines.append(f"\n📊 Total active: {len(sorted_active)}")

        return "\n".join(lines), buttons

    @staticmethod
    def format_listed_notification(decision: ProspectusDecision) -> str:
        """Format notification when a prospectus company gets listed on AMX."""
        return (
            f"✅ <b>{decision.company_name}</b> bonds now listed on AMX!\n"
            f"   ISIN: <code>{decision.amx_isin}</code>\n"
            f"   Prospectus registered: {decision.date}\n"
            f'   <a href="{decision.url}">CBA Decision</a>'
        )
