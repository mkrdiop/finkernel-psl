"""AST typé du PSL (blueprint §4.2).

L'AST représente ce qui a été écrit, avec des types stricts; il n'est pas la
représentation financière normalisée (c'est le rôle de la FIR).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict

from finkernel.psl.ast.execution_terms import ExecutionTerms
from finkernel.psl.types.financial_types import (
    Aggregation, BarrierObservation, BusinessDayConvention, CalendarId, ComparisonOperator,
    ComponentType, Currency, Frequency, LagUnit, RiskMeasure, UnderlyingType, UnpaidCouponPolicy,
)


class ASTNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProductDeclaration(ASTNode):
    id: str
    name: str
    category: str
    subtype: str
    currency: Currency


class NotionalNode(ASTNode):
    amount: Decimal
    currency: Currency


class SettlementNode(ASTNode):
    currency: Currency
    payment_lag: int
    payment_lag_unit: LagUnit


class ContractDeclaration(ASTNode):
    notional: NotionalNode
    inception_date: date
    maturity_date: date
    settlement: SettlementNode


class MarketIdentifier(ASTNode):
    scheme: str
    value: str


class UnderlyingDeclaration(ASTNode):
    id: str
    type: UnderlyingType
    name: str
    currency: Currency
    market_identifier: Optional[MarketIdentifier] = None


class ReferenceAggregationNode(ASTNode):
    aggregation: Aggregation
    underlyings: List[str]


class ObservationSchedule(ASTNode):
    frequency: Frequency
    first_observation: date
    calendar: CalendarId
    business_day_convention: BusinessDayConvention


class ScheduleDeclaration(ASTNode):
    observation_schedule: ObservationSchedule


class ConditionExpression(ASTNode):
    reference: str
    operator: ComparisonOperator
    threshold: Decimal


class MemoryNode(ASTNode):
    enabled: bool
    unpaid_coupon: Optional[UnpaidCouponPolicy] = None


class MemoryCouponComponent(ASTNode):
    id: str
    type: ComponentType = ComponentType.MEMORY_COUPON
    annual_rate: Decimal
    condition: ConditionExpression
    memory: Optional[MemoryNode] = None


class AutocallComponent(ASTNode):
    id: str
    type: ComponentType = ComponentType.AUTOCALL
    start_observation: int
    trigger: ConditionExpression
    terminate_product: bool


class CapitalProtectionComponent(ASTNode):
    id: str
    type: ComponentType = ComponentType.CONDITIONAL_CAPITAL_PROTECTION
    barrier_level: Decimal
    observation: BarrierObservation


PayoffComponent = Union[MemoryCouponComponent, AutocallComponent, CapitalProtectionComponent]


class PSLDocumentAST(ASTNode):
    psl_version: str
    product: ProductDeclaration
    contract: ContractDeclaration
    underlyings: List[UnderlyingDeclaration]
    reference: ReferenceAggregationNode
    schedule: ScheduleDeclaration
    payoff_components: List[PayoffComponent]
    execution: ExecutionTerms
    valuation: Optional[Dict[str, Any]] = None
    risk_measures: List[RiskMeasure] = []
    metadata: Optional[Dict[str, Any]] = None
