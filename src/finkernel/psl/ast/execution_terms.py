"""Typed, fail-closed execution terms required for executable PSL 1.0 contracts."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ExecutionNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PerformanceDefinition(ExecutionNode):
    initial_fixing_date: date
    initial_fixing_source: str
    price_field: Literal["close", "official_close", "adjusted_close"]
    formula: Literal["price_over_initial_minus_one"]
    fx_treatment: Literal["local_currency", "convert_to_product_currency", "quanto"]
    fx_fixing_date: Optional[date] = None
    fx_fixing_source: Optional[str] = None
    fx_quote_convention: Optional[Literal["product_per_underlying", "underlying_per_product"]] = None

    @field_validator("initial_fixing_source", "fx_fixing_source")
    @classmethod
    def nonempty_source(cls, value):
        if value is not None and not value.strip():
            raise ValueError("source must not be empty")
        return value

    @model_validator(mode="after")
    def require_fx_terms(self):
        if self.fx_treatment in ("convert_to_product_currency", "quanto"):
            if not all((self.fx_fixing_date, self.fx_fixing_source, self.fx_quote_convention)):
                raise ValueError("FX conversion/quanto requires fx_fixing_date, fx_fixing_source and fx_quote_convention")
        elif any((self.fx_fixing_date, self.fx_fixing_source, self.fx_quote_convention)):
            raise ValueError("FX fixing fields are forbidden when fx_treatment is local_currency")
        return self


class CouponEconomics(ExecutionNode):
    day_count: Literal["ACT_360", "ACT_365F", "30_360"]
    accrual_start_rule: Literal["inception_date", "previous_observation"]
    accrual_end_rule: Literal["observation_date"]
    payment_date_rule: Literal["observation_date"]
    stub_rule: Literal["short_first", "long_first", "short_last", "long_last"]
    rounding_decimals: int
    rounding_mode: Literal["half_even", "half_up", "down"]

    @field_validator("rounding_decimals")
    @classmethod
    def rounding_range(cls, value):
        if isinstance(value, bool) or not 0 <= value <= 8:
            raise ValueError("rounding_decimals must be an integer in [0, 8]")
        return value


class AutocallRedemption(ExecutionNode):
    principal_fraction: Decimal
    unpaid_coupon_policy: Literal["pay_all", "forfeit"]

    @field_validator("principal_fraction", mode="before")
    @classmethod
    def exact_decimal(cls, value):
        if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, Decimal)):
            raise ValueError("principal_fraction must be an exact YAML integer or decimal")
        return Decimal(value)

    @field_validator("principal_fraction")
    @classmethod
    def positive_principal(cls, value):
        if not value.is_finite() or value <= 0:
            raise ValueError("principal_fraction must be finite and greater than zero")
        return value


class MaturityRedemption(ExecutionNode):
    above_barrier_principal_fraction: Decimal
    below_barrier_formula: Literal["worst_of_performance"]
    equality_treatment: Literal["protected", "unprotected"]

    @field_validator("above_barrier_principal_fraction", mode="before")
    @classmethod
    def exact_decimal(cls, value):
        if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, Decimal)):
            raise ValueError("above_barrier_principal_fraction must be an exact YAML integer or decimal")
        return Decimal(value)

    @field_validator("above_barrier_principal_fraction")
    @classmethod
    def positive_principal(cls, value):
        if not value.is_finite() or value <= 0:
            raise ValueError("above_barrier_principal_fraction must be finite and greater than zero")
        return value


class ExecutionTerms(ExecutionNode):
    performance: PerformanceDefinition
    coupon: CouponEconomics
    same_date_priority: tuple[Literal["coupon", "autocall", "capital_redemption"], ...]
    autocall_redemption: AutocallRedemption
    maturity_redemption: MaturityRedemption
    settlement_calendar: Literal["TARGET", "NYSE", "TOKYO", "LONDON"]
    settlement_business_day_convention: Literal[
        "following", "modified_following", "preceding", "modified_preceding", "unadjusted"
    ]

    @model_validator(mode="after")
    def validate_event_priority(self):
        required = {"coupon", "autocall", "capital_redemption"}
        if len(self.same_date_priority) != 3 or set(self.same_date_priority) != required:
            raise ValueError("same_date_priority must contain coupon, autocall and capital_redemption exactly once")
        return self
