"""Validate PSL and FIR fixtures against their published versioned JSON Schemas."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from finkernel.psl.parser.yaml_parser import parse_yaml_strict


ROOT = Path(__file__).resolve().parents[2]


def load_schema(path):
    schema = json.loads((ROOT / path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def test_phoenix_psl_fixture_conforms_to_psl_1_schema(phoenix_yaml):
    schema = load_schema("schemas/psl/v1/psl.schema.json")
    document = parse_yaml_strict(phoenix_yaml).data
    errors = list(Draft202012Validator(schema).iter_errors(document))
    assert not errors, [error.message for error in errors]


def test_phoenix_fir_golden_conforms_to_fir_1_schema():
    schema = load_schema("schemas/fir/v1/fir.schema.json")
    golden = json.loads((ROOT / "tests/golden/phoenix_fir_v1.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(golden))
    assert not errors, [error.message for error in errors]



def test_fir_schema_accepts_decimal_redemption_fractions_and_restricts_settlement():
    schema = load_schema("schemas/fir/v1/fir.schema.json")
    golden = json.loads((ROOT / "tests/golden/phoenix_fir_v1.json").read_text(encoding="utf-8"))
    golden["execution_terms"]["autocall_redemption"]["principal_fraction"] = "0.95"
    golden["execution_terms"]["maturity_redemption"]["above_barrier_principal_fraction"] = "0.95"
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(golden))
    assert not errors, [error.message for error in errors]

    golden["execution_terms"]["settlement_calendar"] = "UNKNOWN"
    errors = list(validator.iter_errors(golden))
    assert any("settlement_calendar" in str(error.absolute_path) for error in errors)



def test_fir_schema_enforces_canonical_decimal_ranges():
    schema = load_schema("schemas/fir/v1/fir.schema.json")
    golden = json.loads((ROOT / "tests/golden/phoenix_fir_v1.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    invalid_cases = [
        (("terms", "notional", "amount"), "0"),
        (("terms", "notional", "amount"), "-1"),
        (("components", 0, "params", "annual_rate"), "1.01"),
        (("components", 0, "params", "annual_rate"), "-0.01"),
        (("components", 0, "params", "condition", "threshold"), "2.01"),
        (("components", 2, "params", "barrier_level"), "0"),
        (("execution_terms", "autocall_redemption", "principal_fraction"), "0"),
    ]
    for path, value in invalid_cases:
        candidate = json.loads(json.dumps(golden))
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert list(validator.iter_errors(candidate)), (path, value)

    candidate = json.loads(json.dumps(golden))
    candidate["execution_terms"]["performance"].update({
        "fx_treatment": "quanto",
        "quanto_rate": "0",
        "quanto_quote_convention": "product_per_underlying",
    })
    assert list(validator.iter_errors(candidate))



def test_phoenix_psl_schema_requires_coupon_memory(phoenix_yaml):
    schema = load_schema("schemas/psl/v1/psl.schema.json")
    document = parse_yaml_strict(phoenix_yaml).data
    del document["payoff"]["components"][0]["memory"]
    errors = list(Draft202012Validator(schema).iter_errors(document))
    assert errors
