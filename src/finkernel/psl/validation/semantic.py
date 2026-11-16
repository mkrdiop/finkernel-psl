"""Validation sémantique générique (blueprint §4.4) : cohérence du document, hors règles propres à un produit."""
from __future__ import annotations

from finkernel.core.diagnostics import DiagnosticBag
from finkernel.psl.ast.nodes import AutocallComponent, MemoryCouponComponent, PSLDocumentAST
from finkernel.psl.validation import rules
from finkernel.psl.validation.schedule_grid import observation_dates


def validate_semantics(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    _currencies(ast, bag)
    _dates(ast, bag)
    _underlyings(ast, bag)
    _component_ids(ast, bag)
    _condition_references(ast, bag)
    _execution_terms(ast, bag)


def _currencies(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    pccy = ast.product.currency
    if ast.contract.notional.currency != pccy:
        bag.error("E-CCY-MISMATCH",
                  f"Notional currency ({ast.contract.notional.currency.value}) differs from product currency "
                  f"({pccy.value}).", "contract.notional.currency")
    if ast.contract.settlement.currency != pccy:
        bag.error("E-CCY-MISMATCH",
                  f"Settlement currency ({ast.contract.settlement.currency.value}) differs from product currency "
                  f"({pccy.value}).", "contract.settlement.currency")
    foreign = sorted({u.currency.value for u in ast.underlyings if u.currency != pccy})
    treatment = ast.execution.performance.fx_treatment
    if not foreign and treatment != "local_currency":
        bag.error("E-FX-UNNECESSARY", "FX conversion/quanto is declared although every underlying is in product currency.",
                  "execution.performance.fx_treatment")


def _dates(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    c = ast.contract
    obs = ast.schedule.observation_schedule
    if c.inception_date >= c.maturity_date:
        bag.error("E-DATE-ORDER",
                  f"Maturity date ({c.maturity_date}) must be after inception date ({c.inception_date}).",
                  "contract.maturity_date")
    if not (c.inception_date < obs.first_observation <= c.maturity_date):
        bag.error("E-DATE-ORDER",
                  f"First observation ({obs.first_observation}) must be after inception ({c.inception_date}) "
                  f"and not after maturity ({c.maturity_date}).",
                  "schedule.observation_schedule.first_observation")
        return
    dates = observation_dates(obs, c.maturity_date)
    if dates and dates[-1] != c.maturity_date:
        bag.warning("W-SCHEDULE-GRID",
                    f"The last scheduled observation ({dates[-1]}) does not fall on the maturity date "
                    f"({c.maturity_date}); the final observation is not aligned with maturity.",
                    "schedule.observation_schedule")


def _underlyings(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    seen = {}
    for i, u in enumerate(ast.underlyings):
        if u.id in seen:
            bag.error("E-DUPLICATE-ID", f"Duplicate underlying id '{u.id}' (first declared at underlyings[{seen[u.id]}]).",
                      f"underlyings[{i}].id")
        else:
            seen[u.id] = i
    seen_refs = set()
    for j, uid in enumerate(ast.reference.underlyings):
        path = f"reference.underlyings[{j}]"
        if uid not in seen:
            bag.error("E-REF-UNDECLARED", f"Underlying '{uid}' is referenced but not declared.", path)
        if uid in seen_refs:
            bag.error("E-REF-DUPLICATE", f"Underlying '{uid}' is listed more than once in the reference basket.", path)
        seen_refs.add(uid)
    for i, u in enumerate(ast.underlyings):
        if u.id not in seen_refs:
            bag.warning("W-UL-UNUSED", f"Underlying '{u.id}' is declared but not part of the reference basket.",
                        f"underlyings[{i}]")


def _component_ids(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    seen = {}
    for i, comp in enumerate(ast.payoff_components):
        if comp.id in seen:
            bag.error("E-DUPLICATE-ID",
                      f"Duplicate payoff component id '{comp.id}' (first at payoff.components[{seen[comp.id]}]).",
                      f"payoff.components[{i}].id")
        else:
            seen[comp.id] = i


def _condition_references(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    expected = rules.REFERENCE_FOR_AGGREGATION[ast.reference.aggregation]
    for i, comp in enumerate(ast.payoff_components):
        if isinstance(comp, MemoryCouponComponent):
            cond, cpath = comp.condition, f"payoff.components[{i}].condition.reference"
        elif isinstance(comp, AutocallComponent):
            cond, cpath = comp.trigger, f"payoff.components[{i}].trigger.reference"
        else:
            continue
        if cond.reference != expected:
            bag.error("E-REF-AGG-MISMATCH",
                      f"Condition references '{cond.reference}' but the basket aggregation "
                      f"{ast.reference.aggregation.value} yields '{expected}'.", cpath)


def _execution_terms(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    performance = ast.execution.performance
    first_observation = ast.schedule.observation_schedule.first_observation
    if performance.initial_fixing_date > first_observation:
        bag.error("E-FIXING-DATE", "Initial fixing date must not be later than the first observation.",
                  "execution.performance.initial_fixing_date")
    if performance.initial_fixing_date > ast.contract.maturity_date:
        bag.error("E-FIXING-DATE", "Initial fixing date must not be later than maturity.",
                  "execution.performance.initial_fixing_date")
