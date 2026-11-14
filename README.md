# FINKERNEL PSL — Financial Product Specification Language (v1.0)

FINKERNEL PSL is a declarative, strongly-typed, versioned, and compiler-based framework for specifying, validating, compiling, pricing, and risk-analyzing structured financial products.

## Architecture Overview

1. **Financial Product Specification Language (`finkernel_core/`)**:
   - `models.py`: Strict financial types (`Money`, `Notional`, `UnderlyingReference`, `PayoffComponent`, `PSLDocument`) built on Pydantic v2.
   - `validator.py`: Semantic & contract consistency validation (underlyings resolution, dates validation, barrier bounds).
   - `compiler.py`: YAML parser, type checker, semantic validator, and canonical Intermediate Representation (IR) generator.

2. **Execution & Quantitative Engines (`app/`)**:
   - `app/main.py`: FastAPI REST endpoints (`/psl/validate`, `/psl/compile`, `/psl/simulate`, `/api/options/price`, `/api/swaps/price`, `/api/risk/var`).
   - `app/engines/options.py`: Black-Scholes-Merton, CRR Binomial Trees, and Implied Volatility solvers.
   - `app/engines/rates.py`: QuantLib yield curve bootstrapping and Interest Rate Swap pricing.
   - `app/engines/payoff_engine.py`: Multi-asset correlated Monte Carlo Payoff Engine executing compiled PSL Intermediate Representations (e.g., Phoenix Autocallable Worst-Of).

3. **Examples & Tests**:
   - `examples/phoenix_autocall_worst_of.yaml`: Reference PSL v1.0 specification for a 5Y Worst-Of Phoenix Autocallable Note on SX5E, SPX, and NKY.
   - `examples/run_demo.py`: End-to-end demonstration compiling the YAML spec to IR and pricing it via Monte Carlo.
   - `tests/test_compiler.py`: Pytest suite verifying syntax, typing, and semantic error detection.

## Quickstart

```bash
pip install -r requirements.txt
python examples/run_demo.py
pytest
uvicorn app.main:app --reload --port 8000
```
