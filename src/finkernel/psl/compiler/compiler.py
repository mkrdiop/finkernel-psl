from datetime import datetime, timezone
from typing import Optional, List
from finkernel.psl.parser.yaml_parser import parse_yaml_strict
from finkernel.psl.ast.nodes import PSLDocumentAST, ProductDeclaration, ContractDeclaration, NotionalNode, SettlementNode, UnderlyingDeclaration, ReferenceAggregationNode, PayoffComponentNode
from finkernel.psl.validation.semantic import validate_semantics
from finkernel.fir.models import FIRModel
from finkernel.fir.hashing import compute_canonical_hash
from finkernel.core.errors import FinkernelError

class PSLCompiler:
    COMPILER_VERSION = "1.0.0"

    @classmethod
    def compile_yaml(cls, yaml_content: str) -> Tuple_Result:
        pass

    @classmethod
    def compile_yaml(cls, yaml_content: str):
        try:
            raw = parse_yaml_strict(yaml_content)
            
            prod = raw.get("product", {})
            contract = raw.get("contract", {})
            notional = contract.get("notional", {})
            settlement = contract.get("settlement", {})
            
            ast = PSLDocumentAST(
                psl_version=raw.get("psl_version", "1.0"),
                product=ProductDeclaration(
                    id=prod.get("id"),
                    name=prod.get("name"),
                    category=prod.get("category"),
                    subtype=prod.get("subtype"),
                    currency=prod.get("currency")
                ),
                contract=ContractDeclaration(
                    notional=NotionalNode(amount=notional.get("amount"), currency=notional.get("currency")),
                    inception_date=contract.get("inception_date"),
                    maturity_date=contract.get("maturity_date"),
                    settlement=SettlementNode(
                        currency=settlement.get("currency"),
                        payment_lag=settlement.get("payment_lag", 0),
                        payment_lag_unit=settlement.get("payment_lag_unit", "business_days")
                    )
                ),
                underlyings=[UnderlyingDeclaration(**u) for u in raw.get("underlyings", [])],
                reference=ReferenceAggregationNode(**raw.get("reference", {})),
                schedule=raw.get("schedule", {}),
                payoff_components=[
                    PayoffComponentNode(id=c.get("id"), type=c.get("type"), raw_config=c)
                    for c in raw.get("payoff", {}).get("components", [])
                ],
                valuation=raw.get("valuation", {}),
                risk=raw.get("risk", {}),
                metadata=raw.get("metadata")
            )
            
            errors = validate_semantics(ast)
            if errors:
                return False, None, errors
                
            risk_measures = ast.risk.get("measures", []) if isinstance(ast.risk, dict) else ast.risk
            
            fir_body = {
                "product_id": ast.product.id,
                "product_name": ast.product.name,
                "subtype": ast.product.subtype,
                "currency": ast.product.currency,
                "notional": ast.contract.notional.amount,
                "inception_date": ast.contract.inception_date,
                "maturity_date": ast.contract.maturity_date,
                "underlyings": [u.model_dump() for u in ast.underlyings],
                "reference": ast.reference.model_dump(),
                "schedule": ast.schedule,
                "components": [c.raw_config for c in ast.payoff_components],
                "valuation_config": ast.valuation,
                "risk_measures": risk_measures
            }
            
            canonical_hash = compute_canonical_hash(fir_body)
            compiled_at = datetime.now(timezone.utc).isoformat()
            
            fir = FIRModel(
                canonical_hash=canonical_hash,
                compiled_at=compiled_at,
                **fir_body
            )
            
            return True, fir, []
            
        except FinkernelError as e:
            return False, None, [str(e)]
        except Exception as e:
            return False, None, [f"Internal Compiler Error: {str(e)}"]
