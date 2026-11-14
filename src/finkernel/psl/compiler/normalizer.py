"""AST -> FIR (blueprint §4.5, étape « Normalizer »).

Ordre : les collections non significatives (sous-jacents, panier de référence)
sont triées par identifiant; l'ordre des composants de payoff est conservé tel
qu'écrit car il peut être significatif (ordre d'évaluation à date commune).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from finkernel.fir.canonicalizer import canonical_decimal, to_canonical
from finkernel.fir.models import (
    FIRComponent, FIRContract, FIRMoney, FIRObservationSchedule, FIRProduct, FIRReference,
    FIRSettlement, FIRTerms, FIRUnderlying,
)
from finkernel.psl.ast.nodes import (
    AutocallComponent, CapitalProtectionComponent, ConditionExpression, MemoryCouponComponent,
    PayoffComponent, PSLDocumentAST,
)


def _condition(c: ConditionExpression) -> Dict[str, Any]:
    return {"reference": c.reference, "operator": c.operator.value, "threshold": canonical_decimal(c.threshold)}


def _component(c: PayoffComponent) -> FIRComponent:
    if isinstance(c, MemoryCouponComponent):
        params: Dict[str, Any] = {"annual_rate": canonical_decimal(c.annual_rate), "condition": _condition(c.condition)}
        if c.memory is not None:
            params["memory"] = {
                "enabled": c.memory.enabled,
                "unpaid_coupon": c.memory.unpaid_coupon.value if c.memory.unpaid_coupon else None,
            }
        return FIRComponent(id=c.id, kind="MEMORY_COUPON", params=params)
    if isinstance(c, AutocallComponent):
        return FIRComponent(id=c.id, kind="AUTOCALL", params={
            "start_observation": c.start_observation,
            "trigger": _condition(c.trigger),
            "terminate_product": c.terminate_product,
        })
    assert isinstance(c, CapitalProtectionComponent)
    return FIRComponent(id=c.id, kind="CONDITIONAL_CAPITAL_PROTECTION", params={
        "barrier_level": canonical_decimal(c.barrier_level),
        "observation": c.observation.value,
    })


def normalize(ast: PSLDocumentAST) -> Tuple[FIRContract, Optional[Dict[str, Any]], Optional[Dict[str, Any]],
                                            Optional[Dict[str, Any]]]:
    """Retourne (contrat, config de valorisation, config de risque, métadonnées)."""
    c = ast.contract
    obs = ast.schedule.observation_schedule
    contract = FIRContract(
        product=FIRProduct(id=ast.product.id, name=ast.product.name, category=ast.product.category,
                           subtype=ast.product.subtype, currency=ast.product.currency.value),
        terms=FIRTerms(
            notional=FIRMoney(amount=canonical_decimal(c.notional.amount), currency=c.notional.currency.value),
            inception_date=c.inception_date.isoformat(),
            maturity_date=c.maturity_date.isoformat(),
            settlement=FIRSettlement(currency=c.settlement.currency.value, payment_lag=c.settlement.payment_lag,
                                     payment_lag_unit=c.settlement.payment_lag_unit.value),
        ),
        underlyings=[
            FIRUnderlying(
                id=u.id, type=u.type.value, name=u.name, currency=u.currency.value,
                market_identifier=({"scheme": u.market_identifier.scheme, "value": u.market_identifier.value}
                                   if u.market_identifier else None),
            )
            for u in sorted(ast.underlyings, key=lambda u: u.id)
        ],
        reference=FIRReference(aggregation=ast.reference.aggregation.value,
                               underlyings=sorted(ast.reference.underlyings),
                               performance=ast.reference.performance),
        observation_schedule=FIRObservationSchedule(
            frequency=obs.frequency.value, first_observation=obs.first_observation.isoformat(),
            calendar=obs.calendar.value, business_day_convention=obs.business_day_convention.value),
        components=[_component(comp) for comp in ast.payoff_components],
    )
    valuation = to_canonical(ast.valuation) if ast.valuation is not None else None
    risk = {"measures": sorted({m.value for m in ast.risk_measures})} if ast.risk_measures else None
    metadata = to_canonical(ast.metadata) if ast.metadata is not None else None
    return contract, valuation, risk, metadata
