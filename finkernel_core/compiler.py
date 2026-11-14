import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List
import yaml
from finkernel_core.models import PSLDocument
from finkernel_core.validator import PSLValidator


class PSLCompiler:
    COMPILER_VERSION = "0.1.0"

    @classmethod
    def compile_from_yaml(cls, yaml_content: str) -> Tuple[bool, Dict[str, Any], List[str]]:
        try:
            raw_data = yaml.safe_load(yaml_content)
            if not isinstance(raw_data, dict):
                return False, {}, ["Syntax Error: PSL root must be a YAML mapping."]
        except yaml.YAMLError as e:
            return False, {}, [f"YAML Syntax Error: {str(e)}"]

        try:
            doc = PSLDocument(**raw_data)
        except Exception as e:
            return False, {}, [f"Type Checker Error: {str(e)}"]

        semantic_errors = PSLValidator.validate_semantics(doc)
        if semantic_errors:
            return False, {}, semantic_errors

        ir = cls._generate_intermediate_representation(doc)
        return True, ir, []

    @classmethod
    def _generate_intermediate_representation(cls, doc: PSLDocument) -> Dict[str, Any]:
        components_ir = []
        for comp in doc.payoff.get("components", []):
            comp_dict: Dict[str, Any] = {
                "id": comp.id,
                "type": comp.type,
            }
            if comp.annual_rate is not None:
                comp_dict["annual_rate"] = comp.annual_rate
            if comp.condition is not None:
                comp_dict["condition"] = {
                    "reference": comp.condition.reference,
                    "operator": comp.condition.operator,
                    "threshold": comp.condition.threshold,
                }
            if comp.memory is not None:
                comp_dict["memory"] = comp.memory.enabled
            if comp.eligibility is not None:
                comp_dict["eligibility"] = comp.eligibility
            if comp.trigger is not None:
                comp_dict["trigger"] = {
                    "reference": comp.trigger.reference,
                    "operator": comp.trigger.operator,
                    "threshold": comp.trigger.threshold,
                }
            if comp.barrier is not None:
                comp_dict["barrier"] = {
                    "type": comp.barrier.type,
                    "reference": comp.barrier.reference,
                    "level": comp.barrier.level,
                    "monitoring": comp.barrier.monitoring,
                }
            if comp.redemption is not None:
                comp_dict["redemption"] = comp.redemption
            if comp.terminate_product is not None:
                comp_dict["terminate_product"] = comp.terminate_product
            components_ir.append(comp_dict)

        risk_measures = doc.risk if isinstance(doc.risk, list) else doc.risk.get("measures", [])

        canonical_body = {
            "product_id": doc.product.id,
            "product_name": doc.product.name,
            "product_type": doc.product.subtype.value,
            "currency": doc.contract.notional.currency.value,
            "notional": doc.contract.notional.amount,
            "dates": {
                "inception": doc.contract.inception_date,
                "maturity": doc.contract.maturity_date,
                "schedule": doc.schedule,
            },
            "reference": {
                "aggregation": doc.reference.aggregation,
                "underlyings": doc.reference.underlyings,
            },
            "components": components_ir,
            "valuation": {
                "method": doc.valuation.model.method,
                "paths": doc.valuation.model.paths,
                "underlying_model": doc.valuation.model.underlying_model,
            },
            "risk_measures": risk_measures,
        }

        canonical_hash = hashlib.sha256(
            json.dumps(canonical_body, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]

        return {
            "psl_version": doc.psl_version,
            "compiler_version": cls.COMPILER_VERSION,
            "canonical_hash": canonical_hash,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            **canonical_body,
        }
