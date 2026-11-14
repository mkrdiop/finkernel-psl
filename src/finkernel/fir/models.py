"""Financial Intermediate Representation (blueprint §4.6).

* ``FIRContract`` : contenu économique du contrat, seul objet couvert par ``contract_hash``.
  Aucun paramètre de valorisation/risque (ADR-003). Montants en chaînes décimales canoniques.
* ``FIRDocument`` : contrat + configurations (valorisation, risque) chacune avec son
  empreinte, + provenance (non couverte par les hash, donc reproductibles).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

FIR_VERSION = "1.0"


class FIRNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FIRProduct(FIRNode):
    id: str
    name: str
    category: str
    subtype: str
    currency: str


class FIRMoney(FIRNode):
    amount: str
    currency: str


class FIRSettlement(FIRNode):
    currency: str
    payment_lag: int
    payment_lag_unit: str


class FIRTerms(FIRNode):
    notional: FIRMoney
    inception_date: str
    maturity_date: str
    settlement: FIRSettlement


class FIRUnderlying(FIRNode):
    id: str
    type: str
    name: str
    currency: str
    market_identifier: Optional[Dict[str, str]] = None


class FIRReference(FIRNode):
    aggregation: str
    underlyings: List[str]
    performance: Optional[Dict[str, str]] = None


class FIRObservationSchedule(FIRNode):
    frequency: str
    first_observation: str
    calendar: str
    business_day_convention: str


class FIRComponent(FIRNode):
    id: str
    kind: str
    params: Dict[str, Any]


class FIRContract(FIRNode):
    fir_version: str = FIR_VERSION
    product: FIRProduct
    terms: FIRTerms
    underlyings: List[FIRUnderlying]
    reference: FIRReference
    observation_schedule: FIRObservationSchedule
    components: List[FIRComponent]


class FIRProvenance(FIRNode):
    compilation_id: str
    compiled_at: str
    compiler_version: str
    psl_version: str
    fir_version: str
    source_hash: str


class FIRDocument(FIRNode):
    contract: FIRContract
    contract_hash: str
    valuation_config: Optional[Dict[str, Any]] = None
    valuation_hash: Optional[str] = None
    risk_config: Optional[Dict[str, Any]] = None
    risk_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    provenance: FIRProvenance

    # -- accesseurs de commodité (compatibilité avec la v1 du squelette) --------
    @property
    def product_id(self) -> str:
        return self.contract.product.id

    @property
    def canonical_hash(self) -> str:
        return self.contract_hash

    @property
    def compiled_at(self) -> str:
        return self.provenance.compiled_at

    @property
    def underlyings(self) -> List[FIRUnderlying]:
        return self.contract.underlyings

    @property
    def components(self) -> List[FIRComponent]:
        return self.contract.components
