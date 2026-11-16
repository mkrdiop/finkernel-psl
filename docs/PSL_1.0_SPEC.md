# Finkernel PSL 1.0 — Normative Language Contract

**Status:** Normative specification for the M1 compiler baseline  
**Language version:** `psl_version: "1.0"`  
**Current implementation baseline:** compiler `1.0.0`, FIR `1.0`  
**Authority:** This document is the source of truth for PSL 1.0 syntax and semantics. Code, examples and generated schemas MUST conform to it. A code/example mismatch is an implementation defect, not an alternate interpretation of the language.

## 1. Scope and conformance

PSL is a declarative, typed, YAML-based language for describing the contractual and economic terms of financial products. It is not a pricing language. Valuation configuration and risk requests are explicitly separated from contractual terms.

A conforming compiler MUST:

1. accept exactly one YAML mapping document and reject duplicate keys, aliases/anchors, unsafe tags, unknown fields, and ambiguous YAML scalar coercions;
2. reject unsupported `psl_version` values and all invalid or incomplete required structures;
3. preserve exact decimal values (never silently coerce strings, booleans or binary floating-point values into economic numbers);
4. produce path-aware diagnostics and MUST NOT emit FPIR when any error is present;
5. apply no undocumented defaults to material economic or lifecycle terms;
6. produce deterministic canonical contract content and a SHA-256 contract hash for equivalent normalized contracts.

A warning is non-blocking only when it does not leave a material contractual term undefined. Undefined material terms are errors for a contract eligible for execution. An implementation may expose a non-executable draft with diagnostics, but it MUST NOT mark it executable or pass it to the runtime.

## 2. Document structure

The top-level mapping has the following fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `psl_version` | string | yes | Exact language version; PSL 1.0 is `"1.0"`. |
| `product` | mapping | yes | Product identity and denomination. |
| `contract` | mapping | yes | Notional, dates and settlement terms. |
| `underlyings` | sequence | yes | Declared market references. |
| `reference` | mapping | yes | Basket aggregation and performance definition. |
| `schedule` | mapping | yes | Contractual observation schedule. |
| `payoff` | mapping | yes | Ordered contractual payoff components. |
| `valuation` | mapping | no | Explicit model configuration; not part of contract semantics. |
| `risk` | mapping | no | Requested risk measures; not part of contract semantics. |
| `execution` | typed mapping | yes | Fixing, performance, FX, coupon, event-order, redemption and settlement semantics. |\n| `metadata` | mapping | no | Non-contractual descriptive metadata. |

Unknown fields are errors at every closed-schema mapping. Open mappings (`valuation`, `metadata`, and the explicitly extensible reference-performance details) are versioned extension points; their keys and values MUST still be validated by their owning schema before execution.

## 3. Primitive types and representation

- **Identifier:** non-empty string matching `^[A-Za-z0-9][A-Za-z0-9_.-]*$`.
- **String:** non-empty UTF-8 string.
- **Boolean:** YAML `true` or `false`; integers are not booleans.
- **Integer:** YAML integer, not boolean; range checked by field.
- **Decimal:** YAML integer or decimal numeric scalar parsed exactly. Strings, booleans, NaN, infinity and binary floats are forbidden for contractual amounts/rates/ratios.
- **Date:** quoted ISO calendar date `YYYY-MM-DD`. Non-zero-padded dates and invalid calendar dates are errors. The compiler MUST NOT infer a timezone or time-of-day.
- **Enum:** exact, case-sensitive member of the field's closed vocabulary.
- **Sequence order:** significant unless a field explicitly declares set semantics. Payoff component order is preserved.
- **Currencies:** `EUR`, `USD`, `JPY`, `GBP`, `CHF`, `CAD`, `AUD`, `SEK`, `NOK`, `DKK`.

Ratios are fractions of the relevant initial level: `0.70` means 70%, not `70`. Ratio/barrier/condition thresholds are in `(0, 2]`. Annual coupon rates are fractions in `[0, 1]`. Notional is strictly positive. Payment lag is an integer in `[0, 30]`.

## 4. Product and contract

### 4.1 Product

| Field | Type | Required |
|---|---|---:|
| `product.id` | identifier | yes |
| `product.name` | string | yes |
| `product.category` | identifier | yes |
| `product.subtype` | identifier | yes |
| `product.currency` | Currency | yes |

The product currency is the denomination currency for notional and settlement under PSL 1.0. A mismatch is an error.

### 4.2 Contract

| Field | Type | Required |
|---|---|---:|
| `contract.notional.amount` | Decimal, > 0 | yes |
| `contract.notional.currency` | Currency | yes |
| `contract.inception_date` | Date | yes |
| `contract.maturity_date` | Date | yes |
| `contract.settlement.currency` | Currency | yes |
| `contract.settlement.payment_lag` | integer [0, 30] | yes |
| `contract.settlement.payment_lag_unit` | `business_days` or `calendar_days` | yes |

Maturity MUST be strictly after inception. Settlement currency MUST equal product currency. A payment lag unit is mandatory; zero lag is explicit and is not interchangeable with a missing value.

## 5. Underlyings and reference

### 5.1 Underlying declaration

Each `underlyings[]` item has:

| Field | Type | Required |
|---|---|---:|
| `id` | identifier, unique | yes |
| `type` | `equity_index` or `equity` | yes |
| `name` | string | yes |
| `currency` | Currency | yes |
| `market_identifier` | mapping of non-empty `scheme` and `value` strings | no |

Underlying identifiers MUST be unique. Market identifier omission means no external identifier has been supplied; it MUST NOT be replaced with an inferred ticker or vendor mapping.

### 5.2 Reference basket

| Field | Type | Required |
|---|---|---:|
| `reference.aggregation` | `WORST_OF` or `BEST_OF` | yes |
| `reference.underlyings` | non-empty sequence of declared underlying IDs | yes |


Basket IDs MUST be declared, unique within the basket and ordered only where the selected aggregation semantics require order. Every declared underlying not used in the basket is diagnostic-worthy.

**Performance semantics:** the reference MUST identify the initial fixing source/date and the exact normalized performance formula for each basket member. The compiler MUST NOT assume inception date is the fixing date, infer an initial level, or substitute a vendor convention. For the worst-of/best-of aggregate, the selected aggregation is applied to those normalized performances.

**FX semantics:** if an underlying currency differs from product currency, the contract MUST explicitly state whether the payoff uses local-currency performance, FX-converted performance, or a defined quanto treatment, including the required fixing source and date/convention. No implicit FX or quanto treatment is permitted.

> **Implementation conformance gap:** the current AST accepts `reference.performance` as a free-form string mapping and the current semantic validator only warns when it is absent. That is not sufficient for executable PSL 1.0. SFI-6/SFI-7 MUST replace this permissive behavior with a typed, validated structure and fail closed for missing fixing/performance/FX semantics.

## 6. Observation schedule

The required structure is `schedule.observation_schedule`:

| Field | Type | Required |
|---|---|---:|
| `frequency` | `monthly`, `quarterly`, `semi_annual`, `annual` | yes |
| `first_observation` | Date | yes |
| `calendar` | `TARGET`, `NYSE`, `TOKYO`, `LONDON` | yes |
| `business_day_convention` | `following`, `modified_following`, `preceding`, `modified_preceding`, `unadjusted` | yes |

The first observation MUST be after inception and no later than maturity. The schedule is generated by adding the frequency interval in calendar months from the first observation, then applying the named calendar and business-day convention. The exact generated dates, collision handling and end-of-month behavior MUST be deterministic and tested. Calendar identifiers refer to the published calendar definitions bundled with the implementation; a runtime MUST NOT silently substitute another calendar.

## 7. Payoff components

`payoff.components` is a non-empty ordered sequence. Component IDs MUST be unique. Component order is preserved in FPIR. PSL 1.0 currently defines the following discriminated component types.

### 7.1 Memory coupon

Required fields:

- `id`
- `type: memory_coupon`
- `annual_rate`: Decimal in [0, 1], annualized fraction
- `condition`: `reference`, `operator`, `threshold`
- `memory` (optional only when memory is disabled)

Condition operators: `GTE`, `GT`, `LTE`, `LT`. Threshold is a ratio in (0, 2]. The condition reference MUST equal the reference produced by the selected aggregation: `worst_of_performance` or `best_of_performance`.

When `memory.enabled: true`, `memory.unpaid_coupon` is required; PSL 1.0 defines `accumulate`. When disabled, unpaid coupon policy MUST NOT be inferred.

**Additional mandatory economic terms for executable coupons:** accrual start/end rules, day-count convention, coupon payment dates, stub handling, rounding precision/mode and same-date interaction with other components MUST be explicit. The current component schema does not yet encode all these terms; until it does, coupon-bearing contracts are not execution-conformant.

### 7.2 Autocall

Required fields:

- `id`
- `type: autocall`
- `eligibility.start_observation`: integer >= 1 (1-based observation index)
- `trigger`: condition expression
- `terminate_product`: boolean, MUST be `true` for an autocall

An autocall condition uses the same reference and operator/threshold rules as a coupon. The start index MUST fall within the generated observation schedule. Trigger success terminates the product according to the explicitly defined same-date event ordering and redemption rule.

### 7.3 Conditional capital protection

Required fields:

- `id`
- `type: conditional_capital_protection`
- `barrier.level`: ratio in (0, 2]
- `observation: maturity`

The capital barrier MUST be checked against the defined maturity reference performance. The redemption amount above and below the barrier, including equality behavior, participation, currency and rounding, MUST be explicitly specified. It MUST NOT be inferred from the component name.

### 7.4 Phoenix subtype completeness

For `product.subtype: phoenix_autocallable`, exactly one each of `memory_coupon`, `autocall`, and `conditional_capital_protection` is required. No unregistered component is accepted for this subtype.

The contract MUST also define:
- coupon accrual/day count and coupon payment rules;
- coupon/autocall/capital-redemption precedence when dates coincide;
- autocall redemption amount and any accrued/memory coupon treatment;
- maturity redemption formula on both sides of the capital barrier and at equality;
- settlement calendar and payment-date adjustment;
- reference fixing/performance and any FX/quanto treatment.

A compiler MUST reject execution eligibility if any of these terms is absent. Warnings alone are insufficient.

## 8. Valuation and risk are not contract terms

`valuation` is optional and contains model configuration, such as method, path count, underlying model, correlation input and calibration provenance. It MUST be schema-validated by the valuation subsystem. Its values MUST NOT alter `contract_hash`.

`risk.measures` is an optional sequence drawn from `delta`, `gamma`, `vega`, `theta`, `rho`, `value_at_risk`. Risk requests MUST NOT alter `contract_hash`; they are independently normalized and hashed.

`metadata` is descriptive only and MUST NOT alter contract, valuation or risk hashes.

## 9. Canonical FPIR and hash contract

The compiler emits FIR 1.0 with a contract payload containing:

`fir_version`, `product`, `terms`, `underlyings`, `reference`, `observation_schedule`, `components`.

The enclosing document contains:
- `contract` and `contract_hash`;
- optional `valuation_config` and `valuation_hash`;
- optional `risk_config` and `risk_hash`;
- optional `metadata`;
- `provenance`: compilation ID/time, compiler/PSL/FIR versions and source hash.

Hash rules:

1. Contract hash covers only normalized contractual content; it excludes valuation, risk, metadata and provenance.
2. Valuation and risk configurations have independent hashes.
3. Canonical JSON uses UTF-8, sorted object keys, compact separators and deterministic scalar encoding.
4. Decimal values are canonical base-10 strings without exponent notation or insignificant trailing zeroes. Non-finite values and floats are forbidden.
5. Dates use ISO `YYYY-MM-DD`; enums use their exact string values.
6. Semantically unordered collections are normalized deterministically; ordered payoff components retain their order.
7. SHA-256 is lowercase hexadecimal, exactly 64 characters.
8. Source hash is SHA-256 of source text with CRLF normalized to LF. Source hash is provenance, not contract identity.

A change to the meaning, requiredness, type, allowed values or canonical representation of any PSL field requires a new PSL language version. A change to FPIR shape or canonical serialization requires a new FIR version. A compiler implementation fix that preserves both contracts may increment compiler version without changing PSL/FIR versions.

## 10. Diagnostics and fail-closed behavior

Diagnostics MUST expose a stable code, severity (`error` or `warning`), message, field path and source line/column where available. The compiler SHOULD collect independent diagnostics in one pass.

At minimum, errors cover malformed YAML, duplicate keys, unsupported versions, missing/unknown fields, wrong primitive types, invalid dates, invalid enum values, out-of-range amounts/rates/ratios, duplicate IDs, undeclared/duplicate basket members, invalid schedule ordering, invalid component completeness, invalid references and missing material economic terms.

No FPIR may be returned as executable output when any error exists. Internal compiler defects MUST be distinguished from user specification errors.

## 11. Positive and negative examples

The Phoenix example at `examples/phoenix_autocall_worst_of/phoenix_autocall.yaml` is a structural syntax example. It is **not yet an execution-complete reference contract** until its fixing/performance, FX, accrual/day-count, same-date ordering, redemption and settlement-calendar terms are made explicit.

Negative examples MUST include at least: duplicate YAML key; unknown field; unsupported PSL version; unquoted/non-ISO date; boolean used as number; string used as decimal; notional <= 0; ratio > 2; annual coupon > 1; unknown enum; duplicate underlying/component ID; undeclared basket member; invalid date ordering; missing memory policy when enabled; autocall without termination; autocall start outside schedule; missing material fixing/FX/coupon/redemption/event-order terms.

## 12. Compatibility policy

- PSL 1.0 parsers accept only `psl_version: "1.0"`; no implicit migration or fallback.
- Unknown fields are rejected, not ignored.
- A future incompatible grammar or semantic change requires `psl_version: "2.0"` and a separately versioned schema/parser.
- The compiler MUST NOT silently reinterpret old documents under new semantics.
- Canonical FIR compatibility is governed independently by `fir_version`.
- Published product versions are immutable; changing contractual terms creates a new product version.

## 13. M1 implementation conformance checklist

The following are release blockers for PSL 1.0 execution conformance:

- [ ] Replace free-form performance mapping with typed initial-fixing/performance semantics.
- [ ] Define and validate FX/quanto treatment for cross-currency underlyings.
- [ ] Encode coupon accrual, day count, payment schedule, stubs and rounding.
- [ ] Encode deterministic same-date component/event precedence.
- [ ] Encode autocall redemption and coupon settlement treatment.
- [ ] Encode maturity redemption formula, including barrier equality.
- [ ] Encode settlement calendar and business-day adjustment.
- [ ] Publish machine-readable PSL 1.0 schema and positive/negative fixtures.
- [ ] Ensure all semantic omissions above are errors for execution eligibility.
- [ ] Verify compiler and schema behavior with golden, property, negative and compatibility tests in CI.

This checklist is deliberately explicit: the current compiler baseline is not declared fully PSL 1.0 execution-conformant merely because it can compile the existing Phoenix syntax example.


## 14. PSL 1.0 execution contract — normative implementation addendum

The typed, closed-schema `execution` mapping is REQUIRED for all executable PSL 1.0 documents. It is part of the contractual identity and is included in FIR 1.0 `execution_terms`. The former free-form `reference.performance` mapping is not part of PSL 1.0 and MUST be rejected as an unknown field. Performance semantics live only at `execution.performance`.

The machine-readable structural schema is `schemas/psl/v1/psl.schema.json`. Compiler semantic validation remains authoritative for cross-field constraints that JSON Schema cannot express, including uniqueness, date ordering, currency consistency, basket membership, observation ranges and the complete event-priority permutation.

### 14.1 Typed execution fields

`execution.performance` requires:
- `initial_fixing_date`: ISO date, not later than first observation;
- `initial_fixing_source`: non-empty source identifier;
- `price_field`: `close`, `official_close` or `adjusted_close`;
- `formula`: `price_over_initial`;
- `fx_treatment`: `local_currency`, `convert_to_product_currency` or `quanto`.

For conversion or quanto, `fx_fixing_date`, `fx_fixing_source` and `fx_quote_convention` are all mandatory. Quanto additionally requires an explicit positive `quanto_rate`. Quote convention is `product_per_underlying` or `underlying_per_product`. FX fixing fields are forbidden for `local_currency`. Local-currency performance is an explicit choice: each underlying's return is calculated in its own denomination before basket aggregation. The compiler does not infer an FX conversion.

`execution.coupon` requires day count (`ACT_360`, `ACT_365F`, `30_360`), accrual start (`inception_date_for_first_period_then_previous_observation`), accrual end and payment date rules (`observation_date` in PSL 1.0), stub rule (`short_first`, `long_first`, `short_last`, `long_last`), rounding precision [0, 8] and rounding mode (`half_even`, `half_up`, `down`).

`execution.same_date_priority` MUST be a permutation containing exactly once each of `coupon`, `autocall` and `capital_redemption`. This is the contractual precedence order when events share an observation date; it is not inferred from YAML component order.

`execution.autocall_redemption` requires a positive `principal_fraction` and an `unpaid_coupon_policy` of `pay_all` or `forfeit`.

`execution.maturity_redemption` requires a positive `above_barrier_principal_fraction`, `below_barrier_formula: worst_of_performance`, and explicit `equality_treatment: protected | unprotected`. These are distinct from the barrier trigger itself.

Settlement calendar and adjustment are explicit through `execution.settlement_calendar` and `execution.settlement_business_day_convention`. They do not replace the observation calendar.

All execution fields are typed Pydantic AST nodes with extra fields forbidden. Missing, malformed, unknown or internally inconsistent execution terms are compiler errors; no executable FIR is produced. The canonical FIR contract contains the complete normalized execution terms, so changing any of them changes `contract_hash`.

### 14.2 Canonical FIR 1.0 schema

The canonical contract schema is published at `schemas/fir/v1/fir.schema.json`. It formalizes the existing FIR version dimension (`fir_version: "1.0"`) and does not introduce a competing version field. The contract payload includes `execution_terms`; valuation, risk, metadata and provenance remain outside the contractual hash according to the existing hash separation rules.

The executable reference fixture is `examples/phoenix_autocall_worst_of/phoenix_autocall.yaml`; its normalized contract snapshot is `tests/golden/phoenix_fir_v1.json`.
