from typing import List
from finkernel_core.models import PSLDocument


class PSLValidator:
    @staticmethod
    def validate_semantics(doc: PSLDocument) -> List[str]:
        errors: List[str] = []

        declared_underlyings = {u.id for u in doc.underlyings}
        referenced_underlyings = set(doc.reference.underlyings)

        missing = referenced_underlyings - declared_underlyings
        if missing:
            errors.append(
                f"Semantic Error: Underlyings {sorted(missing)} are referenced in 'reference' but not declared in 'underlyings'."
            )

        if doc.contract.inception_date >= doc.contract.maturity_date:
            errors.append(
                f"Semantic Error: Maturity date ({doc.contract.maturity_date}) must be strictly after inception date ({doc.contract.inception_date})."
            )

        contract_ccy = doc.contract.notional.currency
        if doc.contract.settlement.currency != contract_ccy:
            errors.append(
                f"Semantic Error: Settlement currency ({doc.contract.settlement.currency}) differs from notional currency ({contract_ccy}) without explicit FX conversion."
            )

        components = doc.payoff.get("components", [])
        if not components:
            errors.append("Semantic Error: Payoff must contain at least one component.")

        for comp in components:
            if comp.condition and not (0.0 <= comp.condition.threshold <= 5.0):
                errors.append(
                    f"Semantic Error: Threshold for component '{comp.id}' is out of valid bounds ({comp.condition.threshold})."
                )
            if comp.trigger and not (0.0 <= comp.trigger.threshold <= 5.0):
                errors.append(
                    f"Semantic Error: Trigger threshold for component '{comp.id}' is out of valid bounds ({comp.trigger.threshold})."
                )
            if comp.barrier and not (0.0 <= comp.barrier.level <= 5.0):
                errors.append(
                    f"Semantic Error: Barrier level for component '{comp.id}' is out of valid bounds ({comp.barrier.level})."
                )
            if comp.payment and comp.payment.currency != contract_ccy:
                errors.append(
                    f"Type/Currency Error: Component '{comp.id}' pays in {comp.payment.currency} while contract currency is {contract_ccy}."
                )

        return errors
