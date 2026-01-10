"""Data models for bond analysis."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Bond:
    """Data class representing a bond with all its properties."""

    ticker: str
    isin: str
    maturity_date: str
    short_name: Optional[str] = None
    ask_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_yield: Optional[float] = None
    cpn_rate: Optional[float] = None
    cpn_frequency: Optional[str] = None
    par_value: Optional[float] = None
    japanese_yield: Optional[float] = None
