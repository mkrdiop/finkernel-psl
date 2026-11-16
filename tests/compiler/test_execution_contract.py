"""Fail-closed acceptance tests for the typed PSL 1.0 execution contract."""
import copy

import pytest

from helpers import DELETE, codes, dump, mutate


def compile_data(compiler, data):
    return compiler.compile(dump(data))


def test_execution_terms_are_required(compiler, phoenix_data):
    mutate(phoenix_data, "execution", DELETE)
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-MISSING-FIELD" in codes(result)


@pytest.mark.parametrize(
    "path,value",
    [
        ("execution.performance.formula", "unspecified"),
        ("execution.coupon.day_count", "ACT_ACT"),
        ("execution.autocall_redemption.unpaid_coupon_policy", "maybe"),
        ("execution.maturity_redemption.equality_treatment", "infer"),
        ("execution.settlement_calendar", "UNKNOWN"),
    ],
)
def test_unknown_execution_enum_values_are_rejected(compiler, phoenix_data, path, value):
    mutate(phoenix_data, path, value)
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)


def test_unknown_execution_fields_are_rejected(compiler, phoenix_data):
    phoenix_data["execution"]["guess_the_coupon_rule"] = "best effort"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)


def test_same_date_priority_must_be_a_complete_permutation(compiler, phoenix_data):
    phoenix_data["execution"]["same_date_priority"] = ["coupon", "coupon", "autocall"]
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)


def test_fx_conversion_requires_fixing_contract(compiler, phoenix_data):
    phoenix_data["execution"]["performance"]["fx_treatment"] = "convert_to_product_currency"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)


def test_fixing_must_not_follow_first_observation(compiler, phoenix_data):
    phoenix_data["execution"]["performance"]["initial_fixing_date"] = "2027-04-16"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-FIXING-DATE" in codes(result)


def test_execution_terms_are_part_of_contract_identity(compiler, phoenix_data):
    baseline = compile_data(compiler, phoenix_data)
    changed = copy.deepcopy(phoenix_data)
    changed["execution"]["coupon"]["day_count"] = "ACT_360"
    result = compile_data(compiler, changed)
    assert baseline.success and result.success
    assert baseline.fir.contract_hash != result.fir.contract_hash


def test_execution_terms_are_present_in_canonical_fir(compiler, phoenix_yaml):
    result = compiler.compile(phoenix_yaml)
    assert result.success
    payload = result.fir.contract.model_dump(mode="json")
    assert payload["execution_terms"]["performance"]["formula"] == "price_over_initial"
    assert payload["execution_terms"]["same_date_priority"] == ["coupon", "autocall", "capital_redemption"]
    assert result.fir.contract.execution_terms.__class__.__name__ == "FIRExecutionTerms"


def test_quanto_requires_an_explicit_quanto_rate(compiler, phoenix_data):
    terms = phoenix_data["execution"]["performance"]
    terms.update({
        "fx_treatment": "quanto",
        "quanto_quote_convention": "product_per_underlying",
    })
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)


def test_memory_coupon_requires_explicit_enabled_or_disabled_state(compiler, phoenix_data):
    mutate(phoenix_data, "payoff.components[0].memory", DELETE)
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-COUPON-MEMORY-UNSPECIFIED" in codes(result)


def test_unregistered_product_subtype_is_not_executable(compiler, phoenix_data):
    phoenix_data["product"]["subtype"] = "unregistered_product"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-SUBTYPE-UNREGISTERED" in codes(result)


def test_legacy_free_form_reference_performance_is_rejected(compiler, phoenix_data):
    phoenix_data["reference"]["performance"] = {"formula": "guessed"}
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-UNKNOWN-FIELD" in codes(result)


def test_execution_decimal_fields_reject_string_coercion(compiler, phoenix_data):
    phoenix_data["execution"]["autocall_redemption"]["principal_fraction"] = "1.0"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-EXECUTION-TERMS" in codes(result)

def test_disabled_coupon_memory_cannot_carry_an_unpaid_policy(compiler, phoenix_data):
    phoenix_data["payoff"]["components"][0]["memory"] = {
        "enabled": False,
        "unpaid_coupon": "accumulate",
    }
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-UNPAID-COUPON-WHEN-DISABLED" in codes(result)

def test_single_quanto_rate_cannot_cover_multiple_foreign_currencies(compiler, phoenix_data):
    terms = phoenix_data["execution"]["performance"]
    terms.update({
        "fx_treatment": "quanto",
        "quanto_rate": 1.08,
        "quanto_quote_convention": "product_per_underlying",
    })
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-QUANTO-MULTI-CCY" in codes(result)



def test_unquoted_iso_dates_are_rejected(compiler, phoenix_yaml):
    source = phoenix_yaml.replace('inception_date: "2027-01-15"', "inception_date: 2027-01-15", 1)
    result = compiler.compile(source)
    assert not result.success and result.fir is None

    source = phoenix_yaml.replace(
        'initial_fixing_date: "2027-01-14"',
        "initial_fixing_date: 2027-01-14",
        1,
    )
    result = compiler.compile(source)
    assert not result.success and result.fir is None



def test_phoenix_subtype_rejects_best_of_when_maturity_redemption_is_worst_of(compiler, phoenix_data):
    phoenix_data["reference"]["aggregation"] = "BEST_OF"
    phoenix_data["payoff"]["components"][0]["condition"]["reference"] = "best_of_performance"
    phoenix_data["payoff"]["components"][1]["trigger"]["reference"] = "best_of_performance"
    result = compile_data(compiler, phoenix_data)
    assert not result.success and result.fir is None
    assert "E-PHOENIX-AGGREGATION" in codes(result)
