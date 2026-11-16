"""Construit l'AST typé depuis le document brut, en collectant *tous* les diagnostics structurels."""
from __future__ import annotations

from decimal import Decimal
from pydantic import ValidationError
from typing import Any, Dict, Optional

from finkernel.core.diagnostics import DiagnosticBag
from finkernel.psl.ast.execution_terms import ExecutionTerms
from finkernel.psl.ast.nodes import (
    AutocallComponent, CapitalProtectionComponent, ConditionExpression, ContractDeclaration,
    MarketIdentifier, MemoryCouponComponent, MemoryNode, NotionalNode, ObservationSchedule,
    PayoffComponent, ProductDeclaration, PSLDocumentAST, ReferenceAggregationNode,
    ScheduleDeclaration, SettlementNode, UnderlyingDeclaration,
)
from finkernel.psl.types.financial_types import (
    Aggregation, BarrierObservation, BusinessDayConvention, CalendarId, ComparisonOperator,
    ComponentType, Currency, Frequency, LagUnit, RiskMeasure, UnderlyingType, UnpaidCouponPolicy,
)
from finkernel.psl.types.type_checker import MISSING, TypeChecker, join
from finkernel.psl.validation import rules

SUPPORTED_PSL_VERSIONS = ("1.0",)

_RATIO_HINT = "Ratios are written as fractions of the initial level (0.70 means 70%)."


def _none(*values: Any) -> bool:
    return any(v is None for v in values)


def build_ast(raw: Dict[str, Any], bag: DiagnosticBag) -> Optional[PSLDocumentAST]:
    tc = TypeChecker(bag)
    top = tc.fields(
        raw, "",
        required=("psl_version", "product", "contract", "underlyings", "reference", "schedule", "payoff", "execution"),
        optional=("valuation", "risk", "metadata"),
    )
    if top is None:
        return None

    psl_version = tc.string(top.get("psl_version", MISSING), "psl_version", hint='Quote it: psl_version: "1.0".')
    if psl_version is not None and psl_version not in SUPPORTED_PSL_VERSIONS:
        bag.error("E-PSL-VERSION", f"Unsupported PSL version '{psl_version}'. Supported: {list(SUPPORTED_PSL_VERSIONS)}.",
                  "psl_version")
        psl_version = None

    product = _product(tc, top.get("product", MISSING), "product")
    contract = _contract(tc, top.get("contract", MISSING), "contract")
    underlyings = _underlyings(tc, top.get("underlyings", MISSING), "underlyings")
    reference = _reference(tc, top.get("reference", MISSING), "reference")
    schedule = _schedule(tc, top.get("schedule", MISSING), "schedule")
    components = _payoff(tc, top.get("payoff", MISSING), "payoff")
    execution = _execution(tc, top.get("execution", MISSING), "execution")

    valuation = tc.free_mapping(top["valuation"], "valuation") if "valuation" in top else None
    metadata = tc.free_mapping(top["metadata"], "metadata") if "metadata" in top else None
    risk_measures = _risk(tc, top["risk"], "risk") if "risk" in top else []

    if bag.has_errors or _none(psl_version, product, contract, underlyings, reference, schedule, components, execution,
                               risk_measures):
        return None

    return PSLDocumentAST(
        psl_version=psl_version, product=product, contract=contract, underlyings=underlyings,
        reference=reference, schedule=schedule, payoff_components=components, execution=execution, valuation=valuation,
        risk_measures=risk_measures, metadata=metadata,
    )


def _product(tc: TypeChecker, raw: Any, path: str) -> Optional[ProductDeclaration]:
    d = tc.fields(raw, path, required=("id", "name", "category", "subtype", "currency"))
    if d is None:
        return None
    id_ = tc.identifier(d.get("id", MISSING), join(path, "id"))
    name = tc.string(d.get("name", MISSING), join(path, "name"))
    category = tc.identifier(d.get("category", MISSING), join(path, "category"))
    subtype = tc.identifier(d.get("subtype", MISSING), join(path, "subtype"))
    currency = tc.enum(d.get("currency", MISSING), join(path, "currency"), Currency)
    if _none(id_, name, category, subtype, currency):
        return None
    return ProductDeclaration(id=id_, name=name, category=category, subtype=subtype, currency=currency)


def _contract(tc: TypeChecker, raw: Any, path: str) -> Optional[ContractDeclaration]:
    d = tc.fields(raw, path, required=("notional", "inception_date", "maturity_date", "settlement"))
    if d is None:
        return None
    notional = _notional(tc, d.get("notional", MISSING), join(path, "notional"))
    inception = tc.date(d.get("inception_date", MISSING), join(path, "inception_date"))
    maturity = tc.date(d.get("maturity_date", MISSING), join(path, "maturity_date"))
    settlement = _settlement(tc, d.get("settlement", MISSING), join(path, "settlement"))
    if _none(notional, inception, maturity, settlement):
        return None
    return ContractDeclaration(notional=notional, inception_date=inception, maturity_date=maturity,
                               settlement=settlement)


def _notional(tc: TypeChecker, raw: Any, path: str) -> Optional[NotionalNode]:
    d = tc.fields(raw, path, required=("amount", "currency"))
    if d is None:
        return None
    amount = tc.decimal(d.get("amount", MISSING), join(path, "amount"), minimum=Decimal(0), exclusive_min=True)
    currency = tc.enum(d.get("currency", MISSING), join(path, "currency"), Currency)
    if _none(amount, currency):
        return None
    return NotionalNode(amount=amount, currency=currency)


def _settlement(tc: TypeChecker, raw: Any, path: str) -> Optional[SettlementNode]:
    d = tc.fields(raw, path, required=("currency", "payment_lag", "payment_lag_unit"))
    if d is None:
        return None
    currency = tc.enum(d.get("currency", MISSING), join(path, "currency"), Currency)
    lag = tc.integer(d.get("payment_lag", MISSING), join(path, "payment_lag"), minimum=0, maximum=rules.MAX_PAYMENT_LAG)
    unit = tc.enum(d.get("payment_lag_unit", MISSING), join(path, "payment_lag_unit"), LagUnit)
    if _none(currency, lag, unit):
        return None
    return SettlementNode(currency=currency, payment_lag=lag, payment_lag_unit=unit)


def _underlyings(tc: TypeChecker, raw: Any, path: str):
    items = tc.sequence(raw, path)
    if items is None:
        return None
    result = [_underlying(tc, item, f"{path}[{i}]") for i, item in enumerate(items)]
    return None if any(u is None for u in result) else result


def _underlying(tc: TypeChecker, raw: Any, path: str) -> Optional[UnderlyingDeclaration]:
    d = tc.fields(raw, path, required=("id", "type", "name", "currency"), optional=("market_identifier",))
    if d is None:
        return None
    id_ = tc.identifier(d.get("id", MISSING), join(path, "id"))
    type_ = tc.enum(d.get("type", MISSING), join(path, "type"), UnderlyingType)
    name = tc.string(d.get("name", MISSING), join(path, "name"))
    currency = tc.enum(d.get("currency", MISSING), join(path, "currency"), Currency)
    market_id = None
    ok_mid = True
    if "market_identifier" in d:
        mp = join(path, "market_identifier")
        md = tc.fields(d["market_identifier"], mp, required=("scheme", "value"))
        scheme = tc.string(md.get("scheme", MISSING), join(mp, "scheme")) if md is not None else None
        value = tc.string(md.get("value", MISSING), join(mp, "value")) if md is not None else None
        if _none(scheme, value):
            ok_mid = False
        else:
            market_id = MarketIdentifier(scheme=scheme, value=value)
    if _none(id_, type_, name, currency) or not ok_mid:
        return None
    return UnderlyingDeclaration(id=id_, type=type_, name=name, currency=currency, market_identifier=market_id)


def _reference(tc: TypeChecker, raw: Any, path: str) -> Optional[ReferenceAggregationNode]:
    d = tc.fields(raw, path, required=("aggregation", "underlyings"))
    if d is None:
        return None
    aggregation = tc.enum(d.get("aggregation", MISSING), join(path, "aggregation"), Aggregation)
    seq = tc.sequence(d.get("underlyings", MISSING), join(path, "underlyings"))
    ids = None
    if seq is not None:
        parsed = [tc.identifier(v, f"{join(path, 'underlyings')}[{i}]") for i, v in enumerate(seq)]
        ids = None if any(p is None for p in parsed) else parsed
    if _none(aggregation, ids):
        return None
    return ReferenceAggregationNode(aggregation=aggregation, underlyings=ids)


def _schedule(tc: TypeChecker, raw: Any, path: str) -> Optional[ScheduleDeclaration]:
    d = tc.fields(raw, path, required=("observation_schedule",))
    if d is None:
        return None
    op = join(path, "observation_schedule")
    o = tc.fields(d.get("observation_schedule", MISSING), op,
                  required=("frequency", "first_observation", "calendar", "business_day_convention"))
    if o is None:
        return None
    freq = tc.enum(o.get("frequency", MISSING), join(op, "frequency"), Frequency)
    first = tc.date(o.get("first_observation", MISSING), join(op, "first_observation"))
    cal = tc.enum(o.get("calendar", MISSING), join(op, "calendar"), CalendarId)
    bdc = tc.enum(o.get("business_day_convention", MISSING), join(op, "business_day_convention"),
                  BusinessDayConvention)
    if _none(freq, first, cal, bdc):
        return None
    return ScheduleDeclaration(observation_schedule=ObservationSchedule(
        frequency=freq, first_observation=first, calendar=cal, business_day_convention=bdc))


def _condition(tc: TypeChecker, raw: Any, path: str) -> Optional[ConditionExpression]:
    d = tc.fields(raw, path, required=("reference", "operator", "threshold"))
    if d is None:
        return None
    ref = tc.identifier(d.get("reference", MISSING), join(path, "reference"))
    op = tc.enum(d.get("operator", MISSING), join(path, "operator"), ComparisonOperator)
    thr = tc.decimal(d.get("threshold", MISSING), join(path, "threshold"), minimum=Decimal(0),
                     exclusive_min=True, maximum=rules.MAX_RATIO, hint=_RATIO_HINT)
    if _none(ref, op, thr):
        return None
    return ConditionExpression(reference=ref, operator=op, threshold=thr)


def _payoff(tc: TypeChecker, raw: Any, path: str):
    d = tc.fields(raw, path, required=("components",))
    if d is None:
        return None
    cp = join(path, "components")
    items = tc.sequence(d.get("components", MISSING), cp)
    if items is None:
        return None
    result = [_component(tc, item, f"{cp}[{i}]") for i, item in enumerate(items)]
    return None if any(c is None for c in result) else result


def _component(tc: TypeChecker, raw: Any, path: str) -> Optional[PayoffComponent]:
    if not isinstance(raw, dict):
        tc.fields(raw, path)  # émet E-TYPE
        return None
    ctype = tc.enum(raw.get("type", MISSING), join(path, "type"), ComponentType)
    if "type" not in raw:
        tc.bag.error("E-MISSING-FIELD", "Missing required field 'type'.", path)
    if ctype is None:
        return None
    if ctype is ComponentType.MEMORY_COUPON:
        return _coupon(tc, raw, path)
    if ctype is ComponentType.AUTOCALL:
        return _autocall(tc, raw, path)
    return _capital(tc, raw, path)


def _coupon(tc: TypeChecker, raw: Dict[str, Any], path: str) -> Optional[MemoryCouponComponent]:
    d = tc.fields(raw, path, required=("id", "type", "annual_rate", "condition"), optional=("memory",))
    if d is None:
        return None
    id_ = tc.identifier(d.get("id", MISSING), join(path, "id"))
    rate = tc.decimal(d.get("annual_rate", MISSING), join(path, "annual_rate"), minimum=Decimal(0),
                      maximum=rules.MAX_ANNUAL_RATE, hint="Rates are fractions (0.10 means 10%).")
    cond = _condition(tc, d.get("condition", MISSING), join(path, "condition"))
    memory, ok_mem = None, True
    if "memory" in d:
        mp = join(path, "memory")
        md = tc.fields(d["memory"], mp, required=("enabled",), optional=("unpaid_coupon",))
        if md is None:
            ok_mem = False
        else:
            enabled = tc.boolean(md.get("enabled", MISSING), join(mp, "enabled"))
            policy = None
            if "unpaid_coupon" in md:
                policy = tc.enum(md["unpaid_coupon"], join(mp, "unpaid_coupon"), UnpaidCouponPolicy)
                ok_mem = ok_mem and policy is not None
            if enabled and "unpaid_coupon" not in md:
                tc.bag.error("E-MISSING-FIELD",
                             "Field 'unpaid_coupon' is required when memory is enabled (no silent default).", mp)
                ok_mem = False
            if enabled is False and "unpaid_coupon" in md:
                tc.bag.error("E-UNPAID-COUPON-WHEN-DISABLED",
                             "Field 'unpaid_coupon' is forbidden when memory is disabled.", mp)
                ok_mem = False
            if enabled is None:
                ok_mem = False
            elif ok_mem:
                memory = MemoryNode(enabled=enabled, unpaid_coupon=policy)
    if _none(id_, rate, cond) or not ok_mem:
        return None
    return MemoryCouponComponent(id=id_, annual_rate=rate, condition=cond, memory=memory)


def _autocall(tc: TypeChecker, raw: Dict[str, Any], path: str) -> Optional[AutocallComponent]:
    d = tc.fields(raw, path, required=("id", "type", "eligibility", "trigger", "terminate_product"))
    if d is None:
        return None
    id_ = tc.identifier(d.get("id", MISSING), join(path, "id"))
    ep = join(path, "eligibility")
    e = tc.fields(d.get("eligibility", MISSING), ep, required=("start_observation",))
    start = tc.integer(e.get("start_observation", MISSING), join(ep, "start_observation"), minimum=1) \
        if e is not None else None
    trigger = _condition(tc, d.get("trigger", MISSING), join(path, "trigger"))
    term = tc.boolean(d.get("terminate_product", MISSING), join(path, "terminate_product"))
    if _none(id_, start, trigger, term):
        return None
    return AutocallComponent(id=id_, start_observation=start, trigger=trigger, terminate_product=term)


def _capital(tc: TypeChecker, raw: Dict[str, Any], path: str) -> Optional[CapitalProtectionComponent]:
    d = tc.fields(raw, path, required=("id", "type", "barrier", "observation"))
    if d is None:
        return None
    id_ = tc.identifier(d.get("id", MISSING), join(path, "id"))
    bp = join(path, "barrier")
    b = tc.fields(d.get("barrier", MISSING), bp, required=("level",))
    level = tc.decimal(b.get("level", MISSING), join(bp, "level"), minimum=Decimal(0), exclusive_min=True,
                       maximum=rules.MAX_RATIO, hint=_RATIO_HINT) if b is not None else None
    obs = tc.enum(d.get("observation", MISSING), join(path, "observation"), BarrierObservation)
    if _none(id_, level, obs):
        return None
    return CapitalProtectionComponent(id=id_, barrier_level=level, observation=obs)



def _execution(tc: TypeChecker, raw: Any, path: str) -> Optional[ExecutionTerms]:
    mapping = tc.free_mapping(raw, path)
    if mapping is None:
        return None
    try:
        return ExecutionTerms.model_validate(mapping)
    except ValidationError as exc:
        for issue in exc.errors():
            loc = ".".join(str(part) for part in issue.get("loc", ()))
            diagnostic_path = f"{path}.{loc}" if loc else path
            tc.bag.error("E-EXECUTION-TERMS", issue.get("msg", "Invalid execution terms."), diagnostic_path)
        return None


def _risk(tc: TypeChecker, raw: Any, path: str):
    d = tc.fields(raw, path, optional=("measures",))
    if d is None:
        return None
    if "measures" not in d:
        return []
    mp = join(path, "measures")
    seq = tc.sequence(d["measures"], mp, min_len=0)
    if seq is None:
        return None
    parsed = [tc.enum(v, f"{mp}[{i}]", RiskMeasure) for i, v in enumerate(seq)]
    return None if any(p is None for p in parsed) else parsed
