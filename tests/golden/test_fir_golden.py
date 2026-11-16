"""Golden contract serialization for the normative FIR 1.0 Phoenix fixture."""
import json
from pathlib import Path

from finkernel.fir.canonicalizer import canonical_json


def test_phoenix_fir_matches_golden_contract(compiler, phoenix_yaml):
    result = compiler.compile(phoenix_yaml)
    assert result.success, [diagnostic.format() for diagnostic in result.errors]
    golden_path = Path(__file__).parent / "phoenix_fir_v1.json"
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert canonical_json(result.fir.contract) == canonical_json(expected)
    assert len(result.fir.contract_hash) == 64
