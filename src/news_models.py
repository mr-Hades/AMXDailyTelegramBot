"""Data models for CBA prospectus decision tracking."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProspectusDecision:
    """A CBA chairman decision about registering a program prospectus."""

    decision_id: str
    date: str
    title: str
    company_name: str
    url: str
    preview: str = ""
    bond_type: str = ""
    is_supplement: bool = False
    amx_listed: bool = False
    amx_isin: Optional[str] = None

    @property
    def status_label(self) -> str:
        if self.amx_listed:
            return "Listed on AMX"
        return "Active — Pending Placement"
