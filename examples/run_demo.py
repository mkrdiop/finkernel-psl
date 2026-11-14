import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from finkernel_core.compiler import PSLCompiler
from app.engines.payoff_engine import PayoffExecutionEngine


def main():
    yaml_path = os.path.join(os.path.dirname(__file__), "phoenix_autocall_worst_of.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    print("=== 1. Compiling FINKERNEL PSL Specification ===")
    is_valid, ir, errors = PSLCompiler.compile_from_yaml(yaml_content)
    if not is_valid:
        print("Compilation failed:", errors)
        return

    print("Compilation SUCCEEDED!")
    print(json.dumps(ir, indent=2))

    print("\n=== 2. Running Correlated Monte Carlo Payoff Engine ===")
    spots = np.array([4950.0, 5800.0, 38500.0])
    vols = np.array([0.18, 0.16, 0.21])
    corr = np.array([
        [1.00, 0.72, 0.55],
        [0.72, 1.00, 0.50],
        [0.55, 0.50, 1.00],
    ])

    results = PayoffExecutionEngine.simulate_phoenix_ir(
        ir=ir,
        spot_prices=spots,
        volatilities=vols,
        correl_matrix=corr,
        risk_free_rate=0.032,
        num_paths=50000,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
