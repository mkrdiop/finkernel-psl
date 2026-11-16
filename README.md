# FINKERNEL Platform v1.0

*The Engine Behind Financial Innovation.*

FINKERNEL is a software infrastructure to specify, validate, compile, execute and value structured financial products.

## Architecture

1. **PSL** (Financial Product Specification Language): declarative, typed YAML specifications.
2. **PSL Compiler**: strict parser (duplicate keys, aliases and YAML 1.1 coercions rejected), typed AST,
   type checker, semantic and contractual validators, normalizer, structured diagnostics (code, severity, path, line/column).
3. **FIR** (Financial Intermediate Representation): versioned, canonical, pricing-agnostic contract with a SHA-256
   `contract_hash`; valuation and risk configurations have their own hashes; provenance is recorded but never hashed.
4. **Financial Execution Runtime**, 5. **Quantitative engines**: not implemented yet (see `docs/CHANGES.md`).

## Authoritative language contract

The normative PSL 1.0 language contract is [docs/PSL_1.0_SPEC.md](docs/PSL_1.0_SPEC.md).
It defines the grammar's field contract, types, units, enumerations, validation rules,
fail-closed requirements, canonical FPIR/hash semantics and compatibility policy.
The implementation and examples MUST conform to this specification. The executable contract schema is [schemas/psl/v1/psl.schema.json](schemas/psl/v1/psl.schema.json), and the canonical FIR 1.0 schema is [schemas/fir/v1/fir.schema.json](schemas/fir/v1/fir.schema.json). Known implementation
gaps are explicitly tracked in its M1 conformance checklist; a structurally compilable
example is not necessarily eligible for execution.

## Quick start

```bash
pip install -e ".[dev]"      # compiler only needs pydantic + PyYAML
pytest -q
python scripts/run_demo.py
```

```python
from finkernel.psl.compiler.compiler import PSLCompiler

result = PSLCompiler().compile(open("examples/phoenix_autocall_worst_of/phoenix_autocall.yaml").read())
for d in result.diagnostics:
    print(d.severity.value, d.format())
if result.success:
    print(result.fir.contract_hash)
```

Optional extras: `.[quant]` (numpy, scipy, QuantLib), `.[api]` (FastAPI, uvicorn).
