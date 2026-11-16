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
