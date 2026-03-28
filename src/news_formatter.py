"""Telegram message formatting for prospectus notifications."""

from typing import List

from .news_models import ProspectusDecision

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

            messages.append("\n".join(lines))

        return messages
