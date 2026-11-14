from typing import List
from finkernel.psl.ast.nodes import PSLDocumentAST

def validate_semantics(ast: PSLDocumentAST) -> List[str]:
    errors = []
    
    declared = {u.id for u in ast.underlyings}
    referenced = set(ast.reference.underlyings)
    missing = referenced - declared
    if missing:
        errors.append(f"Semantic Error: Underlyings {sorted(missing)} referenced but not declared.")
        
    if ast.contract.inception_date >= ast.contract.maturity_date:
        errors.append(f"Semantic Error: Maturity date ({ast.contract.maturity_date}) must be after inception date ({ast.contract.inception_date}).")
        
    if ast.contract.settlement.currency != ast.product.currency:
        errors.append(f"Semantic Error: Settlement currency ({ast.contract.settlement.currency}) differs from product currency ({ast.product.currency}).")
        
    if not ast.payoff_components:
        errors.append("Semantic Error: Payoff section must contain at least one component.")
        
    return errors
