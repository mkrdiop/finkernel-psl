from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from finkernel_core.compiler import PSLCompiler
from app.models.schemas import PSLSourceRequest, OptionRequest, SwapRequest, VaRRequest
from app.engines.options import OptionEngine
from app.engines.rates import RatesEngine
from app.engines.payoff_engine import PayoffExecutionEngine

app = FastAPI(
    title="FINKERNEL PSL & Quantitative Derivatives Engine",
    version="1.0.0",
    description="Compiler, Validator, and Quantitative Pricing Engine for Financial Product Specification Language (PSL)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "status": "online",
        "product": "FINKERNEL PSL",
        "compiler_version": PSLCompiler.COMPILER_VERSION,
    }


@app.post("/psl/validate")
def validate_psl(req: PSLSourceRequest):
    is_valid, ir, errors = PSLCompiler.compile_from_yaml(req.yaml_content)
    return {
        "status": "VALID" if is_valid else "INVALID",
        "product_id": ir.get("product_id"),
        "psl_version": ir.get("psl_version", "1.0"),
        "compiler_version": PSLCompiler.COMPILER_VERSION,
        "errors": errors,
        "validation": {
            "syntax": "PASSED" if not any("Syntax" in e for e in errors) else "FAILED",
            "types": "PASSED" if not any("Type" in e for e in errors) else "FAILED",
            "semantics": "PASSED" if not any("Semantic" in e for e in errors) else "FAILED",
        },
    }


@app.post("/psl/compile")
def compile_psl(req: PSLSourceRequest):
    is_valid, ir, errors = PSLCompiler.compile_from_yaml(req.yaml_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors})
    return {"status": "COMPILED", "ir": ir}


@app.post("/psl/simulate")
def simulate_psl(req: PSLSourceRequest):
    is_valid, ir, errors = PSLCompiler.compile_from_yaml(req.yaml_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    n = len(ir["reference"]["underlyings"])
    spots = np.array([100.0] * n)
    vols = np.array([0.20] * n)
    corr = np.full((n, n), 0.65)
    np.fill_diagonal(corr, 1.0)

    metrics = PayoffExecutionEngine.simulate_phoenix_ir(
        ir=ir,
        spot_prices=spots,
        volatilities=vols,
        correl_matrix=corr,
        num_paths=min(ir["valuation"]["paths"], 50000),
    )
    return {"status": "SIMULATED", "ir_hash": ir["canonical_hash"], "results": metrics}


@app.post("/api/options/price")
def price_option(req: OptionRequest):
    bs_results = OptionEngine.black_scholes(
        req.spot,
        req.strike,
        req.time_to_maturity,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.option_type,
    )
    tree_price = OptionEngine.binomial_tree(
        req.spot,
        req.strike,
        req.time_to_maturity,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.steps,
        req.option_type,
        req.exercise_style,
    )
    return {
        "black_scholes": bs_results,
        "lattice_price": tree_price,
        "exercise_style": req.exercise_style,
    }


@app.post("/api/options/implied-vol")
def implied_volatility(market_price: float, req: OptionRequest):
    iv = OptionEngine.implied_volatility(
        market_price,
        req.spot,
        req.strike,
        req.time_to_maturity,
        req.risk_free_rate,
        req.dividend_yield,
        req.option_type,
    )
    if iv is None:
        raise HTTPException(status_code=400, detail="Implied volatility solver failed to converge.")
    return {"implied_volatility": iv}


@app.post("/api/swaps/price")
def price_swap(req: SwapRequest):
    try:
        return RatesEngine.bootstrap_and_price_swap(
            req.valuation_date,
            req.notional,
            req.fixed_rate,
            req.swap_tenor_years,
            req.deposit_rate_3m,
            req.swap_rates,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/var")
def calculate_var(req: VaRRequest):
    np.random.seed(42)
    cov_matrix = np.eye(len(req.portfolio_kr01)) * 0.000020**2
    shocks = np.random.multivariate_normal(
        mean=[0] * len(req.portfolio_kr01), cov=cov_matrix, size=req.lookback_days
    )
    scenario_pnl = -np.dot(shocks, np.array(req.portfolio_kr01))
    sorted_pnl = np.sort(scenario_pnl)

    idx = int((1 - req.confidence_level) * len(sorted_pnl))
    var = -sorted_pnl[idx]
    es = -np.mean(sorted_pnl[:idx])

    return {
        "confidence_level": req.confidence_level,
        "var_amount": float(var),
        "expected_shortfall": float(es),
    }
