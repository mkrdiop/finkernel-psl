from datetime import date

from finkernel.psl.compiler.compiler import PSLCompiler
from finkernel.psl.types.financial_types import Frequency
from finkernel.psl.validation.schedule_grid import observation_dates
from finkernel.psl.ast.nodes import ObservationSchedule
from helpers import codes


def test_phoenix_compiles(compiler, phoenix_yaml):
    r = compiler.compile(phoenix_yaml)
    assert r.success and not r.errors
    assert r.fir.product_id == "FK-PHOENIX-001"
    assert len(r.fir.contract_hash) == 64
    assert len(r.fir.components) == 3 and len(r.fir.underlyings) == 3


def test_phoenix_warnings_surface_known_spec_gaps(compiler, phoenix_yaml):
    r = compiler.compile(phoenix_yaml)
    assert set(codes(r, "warning")) == {
        "W-FX-UNSPECIFIED", "W-REF-PERFORMANCE-UNSPECIFIED", "W-SAME-DATE-ORDER-UNSPECIFIED"}


def test_legacy_tuple_api(phoenix_yaml):
    ok, fir, errors = PSLCompiler.compile_yaml(phoenix_yaml)
    assert ok is True and errors == [] and fir.product_id == "FK-PHOENIX-001"
    ok, fir, errors = PSLCompiler.compile_yaml("a: 1\na: 2\n")
    assert ok is False and fir is None and "Duplicate key" in errors[0]


def test_phoenix_has_20_quarterly_observations_ending_at_maturity():
    sched = ObservationSchedule(frequency=Frequency.QUARTERLY, first_observation=date(2027, 4, 15),
                                calendar="TARGET", business_day_convention="modified_following")
    dates = observation_dates(sched, date(2032, 1, 15))
    assert len(dates) == 20 and dates[0] == date(2027, 4, 15) and dates[-1] == date(2032, 1, 15)


def test_month_end_anchoring_does_not_drift():
    sched = ObservationSchedule(frequency=Frequency.MONTHLY, first_observation=date(2027, 1, 31),
                                calendar="TARGET", business_day_convention="following")
    d = observation_dates(sched, date(2027, 5, 31))
    assert [x.isoformat() for x in d] == ["2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31"]


def test_all_errors_reported_at_once(compiler, phoenix_data):
    from helpers import mutate, dump
    mutate(phoenix_data, "contract.notional.amount", -5)
    mutate(phoenix_data, "product.currency", "XYZ")
    mutate(phoenix_data, "schedule.observation_schedule.calendar", "MOON")
    r = compiler.compile(dump(phoenix_data))
    assert not r.success and len(r.errors) == 3


def test_errors_carry_line_and_column(compiler, phoenix_yaml):
    bad = phoenix_yaml.replace('maturity_date: "2032-01-15"', 'maturity_date: "2026-01-15"')
    r = compiler.compile(bad)
    err = next(d for d in r.errors if d.code == "E-DATE-ORDER")
    expected_line = next(i for i, l in enumerate(bad.splitlines(), 1) if "maturity_date" in l)
    assert err.line == expected_line and err.path == "contract.maturity_date"


def test_user_errors_are_never_internal_errors(compiler, phoenix_data):
    from helpers import mutate, dump, DELETE
    for path in ("product", "reference", "contract.notional", "payoff", "underlyings"):
        d = __import__("copy").deepcopy(phoenix_data)
        mutate(d, path, DELETE)
        r = compiler.compile(dump(d))
        assert not r.success and "E-INTERNAL" not in codes(r), path
