from typing import List, Dict, Any
from pydantic import BaseModel

class FIRModel(BaseModel):
    fir_version: str = "1.0"
    canonical_hash: str
    compiled_at: str
    product_id: str
    product_name: str
    subtype: str
    currency: str
    notional: float
    inception_date: str
    maturity_date: str
    underlyings: List[Dict[str, Any]]
    reference: Dict[str, Any]
    schedule: Dict[str, Any]
    components: List[Dict[str, Any]]
    valuation_config: Dict[str, Any]
    risk_measures: List[str]
