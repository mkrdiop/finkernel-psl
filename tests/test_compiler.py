import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from finkernel_core.compiler import PSLCompiler


def test_valid_phoenix_compilation():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "examples", "phoenix_autocall_worst_of.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    is_valid, ir, errors = PSLCompiler.compile_from_yaml(content)
    assert is_valid is True
    assert errors == []
    assert ir["product_id"] == "FK-PHOENIX-001"
    assert ir["notional"] == 100000.0
    assert len(ir["components"]) == 3


def test_undeclared_underlying_error():
    bad_yaml = """
psl_version: "1.0"
product:
  id: "FK-ERR-01"
  name: "Bad Product"
  category: structured_product
  subtype: phoenix_autocallable
  currency: EUR
contract:
  notional: {amount: 100000, currency: EUR}
  inception_date: "2027-01-15"
  maturity_date: "2032-01-15"
  settlement: {currency: EUR, payment_lag: 3, payment_lag_unit: business_days}
underlyings:
  - {id: SX5E, type: equity_index, name: "EURO STOXX 50", currency: EUR}
reference:
  aggregation: WORST_OF
  underlyings: [SX5E, UNKNOWN_INDEX]
schedule: {}
payoff:
  components:
    - {id: coupon, type: memory_coupon, annual_rate: "5%"}
valuation:
  model:
    method: monte_carlo
    paths: 10000
    underlying_model: {type: correlated_lognormal}
    correlation: {source: market_data}
risk: [delta]
"""
    is_valid, _, errors = PSLCompiler.compile_from_yaml(bad_yaml)
    assert is_valid is False
    assert any("UNKNOWN_INDEX" in err for err in errors)
