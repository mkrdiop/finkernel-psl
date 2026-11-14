import numpy as np
from finkernel.psl.compiler.compiler import PSLCompiler
from finkernel.runtime.engine import FinancialExecutionRuntime
from finkernel.runtime.state_machine import ContractState

def test_runtime_autocall_scenario():
    yaml_spec = '''
psl_version: "1.0"
product:
  id: "FK-PHOENIX-001"
  name: "Phoenix Autocallable Worst-of"
  category: "structured_product"
  subtype: "phoenix_autocallable"
  currency: "EUR"
contract:
  notional: {amount: 100000.0, currency: "EUR"}
  inception_date: "2027-01-15"
  maturity_date: "2032-01-15"
  settlement: {currency: "EUR", payment_lag: 3, payment_lag_unit: "days"}
underlyings:
  - {id: "SX5E", type: "equity_index", name: "SX5E", currency: "EUR"}
  - {id: "SPX", type: "equity_index", name: "SPX", currency: "USD"}
reference:
  aggregation: "WORST_OF"
  underlyings: ["SX5E", "SPX"]
schedule:
  observation_schedule: {frequency: "quarterly"}
payoff:
  components:
    - {id: "coupon", type: "memory_coupon", annual_rate: 0.10, condition: {reference: "worst_of_perf", operator: "GTE", threshold: 0.7}, memory: {enabled: true, unpaid_coupon: "accumulate"}}
    - {id: "autocall", type: "autocall", eligibility: {start_observation: 2}, trigger: {reference: "worst_of_perf", operator: "GTE", threshold: 1.0}, terminate_product: true}
    - {id: "capital_redemption", type: "conditional_capital_protection", barrier: {level: 0.6}, observation: "maturity"}
valuation:
  model: {method: "monte_carlo", paths: 1000, underlying_model: {type: "lognormal"}, correlation: {source: "identity"}}
risk: [delta]
'''
    success, fir, errors = PSLCompiler.compile_yaml(yaml_spec)
    assert success is True

    num_obs = 20
    paths = np.ones((num_obs, 2)) * 100.0
    paths[1, :] = 110.0

    initial_spots = np.array([100.0, 100.0])
    result = FinancialExecutionRuntime.execute_simulation(fir, paths, initial_spots)

    assert result["final_state"] == ContractState.TERMINATED.value
    assert result["total_cashflows"] > 0
    assert any(cf["category"] == "redemption" and "Autocall" in cf["origin_event"] for cf in result["cashflows"])
