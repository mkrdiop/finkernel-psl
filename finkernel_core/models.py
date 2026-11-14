from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class CurrencyEnum(str, Enum):
    EUR = "EUR"
    USD = "USD"
    JPY = "JPY"
    GBP = "GBP"
    CHF = "CHF"


class CategoryEnum(str, Enum):
    STRUCTURED_PRODUCT = "structured_product"
    EQUITY_DERIVATIVE = "equity_derivative"
    INTEREST_RATE_DERIVATIVE = "interest_rate_derivative"
    FX_DERIVATIVE = "fx_derivative"


class SubtypeEnum(str, Enum):
    PHOENIX_AUTOCALLABLE = "phoenix_autocallable"
    VANILLA_SWAP = "vanilla_swap"
    BARRIER_NOTE = "barrier_note"


class UnderlyingTypeEnum(str, Enum):
    EQUITY_INDEX = "equity_index"
    EQUITY = "equity"
    ETF = "etf"
    FX = "fx"
    INTEREST_RATE = "interest_rate"
    COMMODITY = "commodity"
    CREDIT_REFERENCE = "credit_reference"


class Money(BaseModel):
    amount: float
    currency: CurrencyEnum


class Notional(BaseModel):
    amount: float = Field(..., gt=0)
    currency: CurrencyEnum


class UnderlyingReference(BaseModel):
    id: str
    type: UnderlyingTypeEnum
    name: str
    currency: CurrencyEnum
    market_identifier: Optional[Dict[str, str]] = None


class ObservationSchedule(BaseModel):
    frequency: str
    first_observation: str
    calendar: str
    business_day_convention: str


class Settlement(BaseModel):
    currency: CurrencyEnum
    payment_lag: int = Field(..., ge=0)
    payment_lag_unit: str


class Contract(BaseModel):
    notional: Notional
    inception_date: str
    maturity_date: str
    settlement: Settlement


class ReferenceAggregation(BaseModel):
    aggregation: str
    underlyings: List[str]
    performance: Optional[Dict[str, str]] = None


class Accrual(BaseModel):
    day_count: str


class PayoffCondition(BaseModel):
    reference: str
    operator: str
    threshold: Union[str, float]

    @field_validator("threshold", mode="before")
    @classmethod
    def parse_percentage(cls, v: Any) -> float:
        if isinstance(v, str) and v.strip().endswith("%"):
            return float(v.strip().rstrip("%")) / 100.0
        return float(v)


class MemoryConfig(BaseModel):
    enabled: bool
    unpaid_coupon: str


class PaymentConfig(BaseModel):
    timing: str
    currency: CurrencyEnum


class BarrierConfig(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = "european"
    reference: Optional[str] = "worst_of_performance"
    level: Union[str, float]
    monitoring: Optional[str] = "maturity_only"

    @field_validator("level", mode="before")
    @classmethod
    def parse_level(cls, v: Any) -> float:
        if isinstance(v, str) and v.strip().endswith("%"):
            return float(v.strip().rstrip("%")) / 100.0
        return float(v)


class PayoffComponent(BaseModel):
    id: str
    type: str
    annual_rate: Optional[Union[str, float]] = None
    accrual: Optional[Accrual] = None
    condition: Optional[PayoffCondition] = None
    memory: Optional[MemoryConfig] = None
    payment: Optional[PaymentConfig] = None
    eligibility: Optional[Dict[str, Any]] = None
    trigger: Optional[PayoffCondition] = None
    redemption: Optional[Dict[str, Any]] = None
    barrier: Optional[BarrierConfig] = None
    observation: Optional[str] = None
    terminate_product: Optional[bool] = None

    @field_validator("annual_rate", mode="before")
    @classmethod
    def parse_rate(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, str) and v.strip().endswith("%"):
            return float(v.strip().rstrip("%")) / 100.0
        return float(v)


class ValuationModel(BaseModel):
    method: str
    paths: int = Field(..., gt=0)
    underlying_model: Dict[str, str]
    correlation: Dict[str, str]


class Valuation(BaseModel):
    model: ValuationModel
    market_data: Optional[Dict[str, Any]] = None


class ProductIdentity(BaseModel):
    id: str
    name: str
    category: CategoryEnum
    subtype: SubtypeEnum
    currency: CurrencyEnum


class PSLDocument(BaseModel):
    psl_version: str
    product: ProductIdentity
    contract: Contract
    underlyings: List[UnderlyingReference]
    reference: ReferenceAggregation
    schedule: Dict[str, Any]
    payoff: Dict[str, List[PayoffComponent]]
    valuation: Valuation
    risk: Union[List[str], Dict[str, List[str]]]
    metadata: Optional[Dict[str, Any]] = None
