"""Vocabulaire fermé du PSL 1.0 (blueprint §4.3)."""
from enum import Enum


class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"
    JPY = "JPY"
    GBP = "GBP"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"


class FinancialType(str, Enum):
    MONEY = "Money"
    CURRENCY = "Currency"
    RATE = "Rate"
    PERCENTAGE = "Percentage"
    PRICE = "Price"
    VOLATILITY = "Volatility"
    PROBABILITY = "Probability"
    QUANTITY = "Quantity"
    RATIO = "Ratio"
    INDEX_LEVEL = "IndexLevel"
    FREQUENCY = "Frequency"
    DATE = "Date"
    DURATION = "Duration"


class Frequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"

    @property
    def months(self) -> int:
        return {"monthly": 1, "quarterly": 3, "semi_annual": 6, "annual": 12}[self.value]


class BusinessDayConvention(str, Enum):
    FOLLOWING = "following"
    MODIFIED_FOLLOWING = "modified_following"
    PRECEDING = "preceding"
    MODIFIED_PRECEDING = "modified_preceding"
    UNADJUSTED = "unadjusted"


class CalendarId(str, Enum):
    TARGET = "TARGET"
    NYSE = "NYSE"
    TOKYO = "TOKYO"
    LONDON = "LONDON"


class LagUnit(str, Enum):
    BUSINESS_DAYS = "business_days"
    CALENDAR_DAYS = "calendar_days"


class Aggregation(str, Enum):
    WORST_OF = "WORST_OF"
    BEST_OF = "BEST_OF"


class ComparisonOperator(str, Enum):
    GTE = "GTE"
    GT = "GT"
    LTE = "LTE"
    LT = "LT"


class UnderlyingType(str, Enum):
    EQUITY_INDEX = "equity_index"
    EQUITY = "equity"


class ComponentType(str, Enum):
    MEMORY_COUPON = "memory_coupon"
    AUTOCALL = "autocall"
    CONDITIONAL_CAPITAL_PROTECTION = "conditional_capital_protection"


class UnpaidCouponPolicy(str, Enum):
    ACCUMULATE = "accumulate"


class BarrierObservation(str, Enum):
    MATURITY = "maturity"


class RiskMeasure(str, Enum):
    DELTA = "delta"
    GAMMA = "gamma"
    VEGA = "vega"
    THETA = "theta"
    RHO = "rho"
    VALUE_AT_RISK = "value_at_risk"
