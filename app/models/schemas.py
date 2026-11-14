from pydantic import BaseModel, Field
from typing import List


class PSLSourceRequest(BaseModel):
    yaml_content: str = Field(..., description="Raw YAML content of a FINKERNEL PSL document")


class OptionRequest(BaseModel):
    spot: float = Field(..., gt=0, description="Underlying Spot Price")
    strike: float = Field(..., gt=0, description="Strike Price")
    time_to_maturity: float = Field(..., gt=0, description="Time to Maturity in Years")
    risk_free_rate: float = Field(..., description="Continuous Risk-Free Rate")
    dividend_yield: float = Field(0.0, description="Continuous Dividend Yield")
    volatility: float = Field(..., gt=0, description="Volatility (sigma)")
    option_type: str = Field("call", description="'call' or 'put'")
    exercise_style: str = Field("european", description="'european' or 'american'")
    steps: int = Field(100, gt=0, description="Steps for Binomial/Trinomial trees")


class SwapRequest(BaseModel):
    valuation_date: str = Field("2026-11-14", description="YYYY-MM-DD")
    notional: float = Field(10_000_000, gt=0)
    fixed_rate: float = Field(..., gt=0)
    swap_tenor_years: int = Field(5, gt=0)
    deposit_rate_3m: float = Field(0.045)
    swap_rates: List[float] = Field([0.0465, 0.0480, 0.0490], description="2Y, 5Y, 10Y swap rates")


class VaRRequest(BaseModel):
    notional: float = Field(10_000_000, gt=0)
    portfolio_kr01: List[float] = Field(..., description="Key rate DV01 vector across 4 pillars")
    lookback_days: int = Field(250, gt=0)
    confidence_level: float = Field(0.99, gt=0, lt=1)
