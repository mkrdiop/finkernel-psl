"""Financial Product Compiler (blueprint §4.5).

Pipeline : Parser -> AST/Type checker -> Semantic validator -> Contract validator
-> Normalizer -> FIR -> sérialisation canonique -> hash.
Le compilateur ne fait ni pricing ni simulation.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from finkernel.core.diagnostics import Diagnostic, DiagnosticBag
from finkernel.core.errors import PSLSyntaxError
from finkernel.fir.hashing import compute_canonical_hash, sha256_text
from finkernel.fir.models import FIR_VERSION, FIRDocument, FIRProvenance
from finkernel.psl.compiler.ast_builder import build_ast
from finkernel.psl.compiler.normalizer import normalize
from finkernel.psl.parser.yaml_parser import parse_yaml_strict
from finkernel.psl.validation.contractual import validate_contract
from finkernel.psl.validation.semantic import validate_semantics

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompilationResult:
    success: bool
    fir: Optional[FIRDocument]
    diagnostics: Tuple[Diagnostic, ...]

    @property
    def errors(self) -> List[Diagnostic]:
        return [d for d in self.diagnostics if d.severity.value == "error"]

    @property
    def warnings(self) -> List[Diagnostic]:
        return [d for d in self.diagnostics if d.severity.value == "warning"]


class PSLCompiler:
    COMPILER_VERSION = "1.0.0"

    def __init__(self, clock: Optional[Callable[[], datetime]] = None,
                 id_factory: Optional[Callable[[], str]] = None) -> None:
        # Horloge et générateur d'identifiants injectables => tests déterministes.
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: str(uuid.uuid4()))

    def compile(self, source: str) -> CompilationResult:
        bag = DiagnosticBag()
        try:
            try:
                parsed = parse_yaml_strict(source)
            except PSLSyntaxError as e:
                bag.error("E-SYNTAX", str(e), line=e.line, column=e.column)
                return CompilationResult(False, None, tuple(bag.items))

            bag.locator = parsed.source_map.locate
            ast = build_ast(parsed.data, bag)
            if ast is None or bag.has_errors:
                return CompilationResult(False, None, tuple(bag.items))

            validate_semantics(ast, bag)
            validate_contract(ast, bag)
            if bag.has_errors:
                return CompilationResult(False, None, tuple(bag.items))

            contract, valuation, risk, metadata = normalize(ast)
            provenance = FIRProvenance(
                compilation_id=self._id_factory(),
                compiled_at=self._clock().isoformat(),
                compiler_version=self.COMPILER_VERSION,
                psl_version=ast.psl_version,
                fir_version=FIR_VERSION,
                source_hash=sha256_text(source.replace("\r\n", "\n")),
            )
            fir = FIRDocument(
                contract=contract,
                contract_hash=compute_canonical_hash(contract),
                valuation_config=valuation,
                valuation_hash=compute_canonical_hash(valuation) if valuation is not None else None,
                risk_config=risk,
                risk_hash=compute_canonical_hash(risk) if risk is not None else None,
                metadata=metadata,
                provenance=provenance,
            )
            return CompilationResult(True, fir, tuple(bag.items))
        except Exception as e:  # défaut du compilateur, pas erreur de spécification
            log.exception("Internal compiler error")
            bag.error("E-INTERNAL",
                      f"Internal compiler error ({type(e).__name__}). This is a compiler defect, "
                      "not an error in the specification.")
            return CompilationResult(False, None, tuple(bag.items))

    @classmethod
    def compile_yaml(cls, yaml_content: str):
        """API de compatibilité v1 : ``(success, fir, [messages d'erreur])``."""
        result = cls().compile(yaml_content)
        return result.success, result.fir, [d.format() for d in result.errors]
