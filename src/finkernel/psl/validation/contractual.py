"""Règles contractuelles propres à un sous-type de produit (blueprint §4.4 : complétude, terminaison, branches)."""
from __future__ import annotations

from collections import Counter

from finkernel.core.diagnostics import DiagnosticBag
from finkernel.psl.ast.nodes import (
    AutocallComponent, CapitalProtectionComponent, MemoryCouponComponent, PSLDocumentAST,
)
from finkernel.psl.validation import rules
from finkernel.psl.validation.schedule_grid import observation_dates


def validate_contract(ast: PSLDocumentAST, bag: DiagnosticBag) -> None:
    subtype = ast.product.subtype
    required = rules.REQUIRED_COMPONENTS.get(subtype)
    if required is None:
        bag.warning("W-SUBTYPE-UNREGISTERED",
                    f"No contractual rules are registered for subtype '{subtype}'; completeness of the "
                    "contract was not checked.", "product.subtype")
        return

    counts = Counter(c.type for c in ast.payoff_components)
    for ctype in required:
        if counts[ctype] != 1:
            bag.error("E-CONTRACT-COMPONENTS",
                      f"Subtype '{subtype}' requires exactly one '{ctype.value}' component, found {counts[ctype]} "
                      "(undefined contractual branch).", "payoff.components")
    for i, comp in enumerate(ast.payoff_components):
        if comp.type not in required:
            bag.error("E-CONTRACT-COMPONENTS",
                      f"Component type '{comp.type.value}' is not allowed for subtype '{subtype}'.",
                      f"payoff.components[{i}].type")

    coupon = next((c for c in ast.payoff_components if isinstance(c, MemoryCouponComponent)), None)
    autocall = next((c for c in ast.payoff_components if isinstance(c, AutocallComponent)), None)
    capital = next((c for c in ast.payoff_components if isinstance(c, CapitalProtectionComponent)), None)
    idx = {id(c): i for i, c in enumerate(ast.payoff_components)}

    if autocall is not None:
        base = f"payoff.components[{idx[id(autocall)]}]"
        if not autocall.terminate_product:
            bag.error("E-AUTOCALL-NO-TERMINATION",
                      "An autocall component must terminate the product (terminate_product: true); otherwise "
                      "the termination rule is undefined.", f"{base}.terminate_product")
        n_obs = len(observation_dates(ast.schedule.observation_schedule, ast.contract.maturity_date))
        if autocall.start_observation > n_obs:
            bag.error("E-AUTOCALL-START-RANGE",
                      f"Autocall starts at observation {autocall.start_observation} but the schedule only has "
                      f"{n_obs} observation(s): the autocall could never trigger.",
                      f"{base}.eligibility.start_observation")

    if capital is not None and autocall is not None:
        if capital.barrier_level > autocall.trigger.threshold:
            bag.error("E-BARRIER-ORDER",
                      f"Capital barrier ({capital.barrier_level}) exceeds the autocall threshold "
                      f"({autocall.trigger.threshold}).",
                      f"payoff.components[{idx[id(capital)]}].barrier.level")
    if capital is not None and coupon is not None and capital.barrier_level > coupon.condition.threshold:
        bag.warning("W-BARRIER-ORDER",
                    f"Capital barrier ({capital.barrier_level}) is above the coupon barrier "
                    f"({coupon.condition.threshold}); this is unusual for a Phoenix.",
                    f"payoff.components[{idx[id(capital)]}].barrier.level")

    if coupon is not None and autocall is not None:
        bag.warning("W-SAME-DATE-ORDER-UNSPECIFIED",
                    "Coupon and autocall can both trigger on the same observation date; the evaluation and "
                    "payment order is not specified in the contract (blueprint §5.2).", "payoff.components")
