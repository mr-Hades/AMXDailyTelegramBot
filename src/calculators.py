"""Yield calculation services."""

from datetime import datetime
from typing import Optional

from .models import Bond


class CouponParser:
    """Parser for coupon-related data."""

    FREQUENCY_MAP = {
        "Monthly": 12,
        "Quarterly": 4,
        "Semi-Annually": 2,
        "Annually": 1,
        "Annual": 1,
    }

    @staticmethod
    def parse_rate(cpn_rate_str) -> Optional[float]:
        """Parse coupon rate string (Armenian format uses comma as decimal separator)."""
        if not cpn_rate_str or cpn_rate_str == "None":
            return None
        try:
            return float(str(cpn_rate_str).replace(",", "."))
        except (ValueError, TypeError):
            return None

    @classmethod
    def get_payments_per_year(cls, frequency: Optional[str]) -> Optional[int]:
        """Convert frequency string to number of payments per year."""
        if not frequency:
            return None
        return cls.FREQUENCY_MAP.get(frequency)


class JapaneseYieldCalculator:
    """
    Calculator for Japanese Yield (Simple Yield to Maturity).

    Formula: ((Annual Coupon + Annual Capital Gain/Loss) / Price) * 100

    Where:
    - Annual Coupon = Par Value × Coupon Rate
    - Annual Capital Gain/Loss = (Par Value - Purchase Price) / Years to Maturity
    """

    def calculate(self, bond: Bond) -> Optional[float]:
        """Calculate Japanese yield for a bond."""
        if not self._validate_inputs(bond):
            return None

        years_to_maturity = self._calculate_years_to_maturity(bond.maturity_date)
        if years_to_maturity is None or years_to_maturity <= 0:
            return None

        # Price as actual value (ask_price is percentage of par)
        actual_price = (bond.ask_price / 100) * bond.par_value

        # Annual coupon payment
        annual_coupon = (bond.cpn_rate / 100) * bond.par_value

        # Annual capital gain/loss
        annual_capital_gain = (bond.par_value - actual_price) / years_to_maturity

        # Japanese Yield
        if actual_price > 0:
            japanese_yield = ((annual_coupon + annual_capital_gain) / actual_price) * 100
            return round(japanese_yield, 2)

        return None

    def _validate_inputs(self, bond: Bond) -> bool:
        """Validate that all required inputs are present."""
        return all(
            [
                bond.ask_price is not None,
                bond.cpn_rate is not None,
                bond.par_value is not None,
                bond.maturity_date is not None,
            ]
        )

    def _calculate_years_to_maturity(self, maturity_date_str: str) -> Optional[float]:
        """Calculate years from now to maturity date."""
        try:
            maturity_date = datetime.strptime(maturity_date_str, "%Y-%m-%d")
            today = datetime.now()
            return (maturity_date - today).days / 365.25
        except (ValueError, TypeError):
            return None
