from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CashflowRecord(BaseModel):
    cashflow_id: str
    product_id: str
    generation_date: str
    payment_date: str
    amount: float
    currency: str
    category: str  # 'coupon', 'redemption', 'principal'
    origin_event: str
    rule_id: str
    status: str = "PENDING"  # PENDING, SETTLED
