from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ASTNode(BaseModel):
    pass

class ProductDeclaration(ASTNode):
    id: str
    name: str
    category: str
    subtype: str
    currency: str

class NotionalNode(ASTNode):
    amount: float
    currency: str

class SettlementNode(ASTNode):
    currency: str
    payment_lag: int
    payment_lag_unit: str

class ContractDeclaration(ASTNode):
    notional: NotionalNode
    inception_date: str
    maturity_date: str
    settlement: SettlementNode

class UnderlyingDeclaration(ASTNode):
    id: str
    type: str
    name: str
    currency: str
    market_identifier: Optional[Dict[str, str]] = None

class ReferenceAggregationNode(ASTNode):
    aggregation: str
    underlyings: List[str]
    performance: Optional[Dict[str, str]] = None

class PayoffComponentNode(ASTNode):
    id: str
    type: str
    raw_config: Dict[str, Any]

class PSLDocumentAST(ASTNode):
    psl_version: str
    product: ProductDeclaration
    contract: ContractDeclaration
    underlyings: List[UnderlyingDeclaration]
    reference: ReferenceAggregationNode
    schedule: Dict[str, Any]
    payoff_components: List[PayoffComponentNode]
    valuation: Dict[str, Any]
    risk: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
