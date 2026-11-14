import os
import sys
from finkernel.psl.compiler.compiler import PSLCompiler

def test_compiler_success():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "phoenix_autocall_worst_of", "phoenix_autocall.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    success, fir, errors = PSLCompiler.compile_yaml(content)
    assert success is True
    assert errors == []
    assert fir.product_id == "FK-PHOENIX-001"
    assert len(fir.canonical_hash) == 16
