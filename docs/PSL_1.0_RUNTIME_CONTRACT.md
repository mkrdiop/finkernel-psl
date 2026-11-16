# PSL 1.0 Runtime Contract

**Document ID:** FINKERNEL-PSL-1.0-RUNTIME  
**Status:** Normative companion contract for PSL 1.0 / FIR 1.0  
**Applies to:** Runtime schedule resolution, event compilation and ordering, fixing admission, lifecycle reduction, settlement-date calculation, deterministic replay and execution provenance  
**Authority:** This document clarifies runtime behavior already required or implied by `docs/PSL_1.0_SPEC.md`. It does not amend PSL syntax, AST fields, FIR 1.0 shape, canonical serialization or contract hashing. If a rule below cannot be demonstrated to preserve PSL 1.0 meaning, it is an execution restriction, not permission to infer new semantics.

## 1. Conformance language and boundary

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT and MAY are normative.

A runtime-conforming implementation MUST accept only validated FIR `1.0` whose originating PSL version is exactly `1.0`. It MUST verify the FIR schema, contract hash and required execution terms before scheduling any event.

Compiler success is necessary but not sufficient for execution. The runtime MUST perform an execution-eligibility preflight. If a contract depends on any item listed in §8, or any required input/calendar fact is unavailable or ambiguous, the runtime MUST reject execution before emitting contractual cashflows.

The runtime is a deterministic contractual reducer. It MUST NOT price, simulate, interpolate, carry forward fixings, infer terms, silently substitute calendars, or mutate contractual economics. Quantitative valuation engines are downstream consumers of the runtime's cashflow ledger and are outside this contract.

The pure execution core MUST be a deterministic function of:
- validated FIR 1.0;
- immutable calendar bundle and its content hash;
- fixing snapshot and its content hash;
- explicitly supplied runtime/event-schema version;
- any other explicitly versioned execution input required by the FIR.

Wall-clock time, random identifiers, process order, host locale, machine timezone and external mutable services MUST NOT affect canonical business output.

## 2. PSL 1.0 / FIR 1.0 version governance

1. PSL 1.0 remains frozen in meaning. No rule here changes the compiler's accepted language or changes the economic meaning of a previously valid field.
2. This document is a controlled runtime clarification. It MUST be versioned independently from the PSL language and FIR schema.
3. No change to FIR 1.0 structure, canonical serialization or contract hash is permitted under this document.
4. New economic behavior, new contractual alternatives or any choice that cannot be proved semantics-preserving is reserved for PSL 1.1 or a later explicitly versioned contract.
5. A runtime MUST report the PSL version, FIR version, compiler version, runtime version, event-schema version, calendar bundle identifier/hash and fixing snapshot identifier/hash used for every run.
6. Historical runs MUST remain reproducible using the exact referenced immutable input artifacts. A changed calendar or fixing snapshot is a different execution input and MUST NOT overwrite the prior run's provenance.

## 2.1 Normative decision register

The following fifteen decisions are the runtime clarification register. Their detailed requirements are normative in the referenced sections.

| # | Decision | Contract section |
|---|---|---|
| D01 | Original-anchor month schedule generation; anchored EOM and non-EOM day restoration | §3.1 |
| D02 | Preserve nominal/adjusted dates and reject adjusted-date collisions | §3.3 |
| D03 | Immutable, versioned calendar bundle with provenance and content hash | §3.2 |
| D04 | Fail closed for missing calendar data, hash mismatch and unsupported date range | §3.2 |
| D05 | Exactly one authoritative fixing per underlying/date/field/source key | §4.1 |
| D06 | No carry-forward, interpolation, nearest-date, source substitution or partial-basket evaluation | §4.1 |
| D07 | Initial fixing uses its explicit date; scheduled fixings use adjusted observation dates; no independent fixing calendar | §4.2 and §8 |
| D08 | Contract-level payment lag applies uniformly to coupon and principal, anchored at adjusted contractual event date | §5 |
| D09 | Observation and settlement calendars are distinct and independently resolved | §3.2 and §5 |
| D10 | Typed event vocabulary and mandatory fixing/component/settlement phases | §6 |
| D11 | Exact same-date priority permutation is authoritative; all six permutations are conformance cases | §6.3 and §7 |
| D12 | Deterministic coupon-memory/autocall policy interaction and terminal short-circuit | §7 |
| D13 | Explicit lifecycle states; autocall/maturity are contractual terminal states; no discretionary early termination | §9 |
| D14 | Deterministic event IDs, idempotent replay and duplicate-action rejection | §10 |
| D15 | Immutable execution provenance for compiler/runtime/event-schema and calendar/fixing inputs | §2 and §11 |

A decision is not implemented merely because it appears in this register. It is a normative acceptance requirement and MUST be covered by one or more vectors in the conformance package.

## 3. Schedule construction and calendar resolution

### 3.1 Nominal schedule generation

The first observation date is the immutable schedule anchor. For every PSL 1.0 month-based frequency (monthly, quarterly, semi-annual and annual), each nominal date MUST be generated directly from that original anchor by adding the corresponding integer number of calendar months. An adjusted observation date MUST NEVER become the anchor for a later date.

End-of-month rule:
- If the anchor is the final calendar day of its month, every generated nominal date MUST be the final calendar day of its target month.
- Otherwise, preserve the anchor's day number and clamp to the final day of a shorter target month. The original anchor day MUST be restored in later months that contain it.

Examples:
- 2024-01-31 monthly → 2024-01-31, 2024-02-29, 2024-03-31, 2024-04-30, 2024-05-31.
- 2024-01-30 monthly → 2024-01-30, 2024-02-29, 2024-03-30, 2024-04-30, 2024-05-30.

Generate dates through maturity, inclusive, and stop before the first nominal date after maturity. Preserve both nominal and adjusted dates in the execution trace. The schedule's contractual observation index refers to the ordered nominal schedule; adjustment MUST NOT renumber observations.

This rule fixes the path-dependent drift that would result from repeatedly adding months to a previously clamped or adjusted date. It is a deterministic interpretation of the existing PSL §6 requirement to add frequency intervals from the first observation anchor.

### 3.2 Calendar bundle

The observation calendar and settlement calendar are separate roles and MUST be resolved independently. The observation calendar adjusts observation dates. The settlement calendar adjusts payment dates and counts business-day payment lags.

A calendar bundle MUST be immutable and versioned. Its manifest MUST include:
- stable bundle identifier and semantic version;
- source/provenance for each named calendar;
- supported date range for each calendar;
- deterministic holiday/weekend data representation;
- a cryptographic content hash over canonical calendar data.

A holiday-data correction creates a new bundle version and hash. Existing versions remain retrievable for replay. Runtime MUST NOT silently replace an unavailable requested calendar with another calendar or with a host operating-system calendar.

A date outside the declared supported range, a missing calendar identifier, a missing holiday datum needed to resolve a date, or a bundle/hash mismatch MUST cause fail-closed rejection. No extrapolation is permitted.

### 3.3 Business-day adjustment and collisions

Apply the exact `business_day_convention` from the FIR using the named observation calendar. `unadjusted` preserves the nominal date. Modified conventions use the standard month-boundary test: apply following/preceding; if the result crosses the nominal calendar month, use the opposite direction from the nominal date.

If two distinct nominal observations resolve to the same adjusted observation date, the schedule is invalid for execution. The runtime MUST reject the complete schedule with a stable collision diagnostic. It MUST NOT deduplicate, merge, reorder or silently skip either observation.

The nominal date, adjusted observation date and resulting payment date are distinct values and MUST remain distinguishable in trace/provenance.

## 4. Fixing admission and reference inputs

### 4.1 Exact fixing cardinality

For each required key `(underlying_id, fixing_date, price_field, fixing_source)`, the supplied fixing snapshot MUST contain exactly one authoritative value.

- Zero matching values: reject as missing.
- More than one matching value: reject as duplicate, even if values are numerically equal.
- Conflicting source, field or date: reject as ambiguous.
- A partial basket: reject the observation; do not calculate a partial WORST_OF or BEST_OF result.

The runtime MUST NOT carry forward a prior fixing, interpolate, use a nearest date, substitute a vendor/source, infer a close field, or fill a missing basket member.

### 4.2 Fixing dates

Initial fixing MUST use the exact `initial_fixing_date` and `initial_fixing_source` in FIR. Scheduled observation fixings MUST use the corresponding adjusted observation date and the declared `initial_fixing_source`/price-field contract unless the FIR explicitly contains a distinct source for that purpose. PSL 1.0 does not define an independent fixing calendar or a fixing-date fallback convention.

A fixing record MUST retain source, underlying identifier, price field, fixing date, value, currency where applicable and source-record identity. The fixing snapshot MUST be immutable and content-addressed for the duration of a run.

### 4.3 FX and quanto boundaries

The runtime MUST implement only the exact FX treatment represented by FIR 1.0. It MUST reject any attempt to infer FX treatment or use an unsupported per-currency quanto mapping. A PSL 1.0 quanto contract is execution-eligible only when it satisfies the existing single-rate/single-foreign-currency compiler constraints and all explicit quote-convention terms.

## 5. Settlement date calculation

The contract-level `payment_lag` and `payment_lag_unit` apply uniformly to every contractual coupon and principal cashflow. There is no separate implicit lag for a cashflow type.

The lag anchor is the adjusted contractual event date:
- Coupon: adjusted observation date on which the coupon payment obligation is generated.
- Autocall principal: adjusted observation date on which autocall redemption is generated.
- Maturity principal: adjusted maturity event date under the observation schedule/maturity rule.

Calculation:
1. Start from the adjusted contractual event date.
2. If lag unit is `calendar_days`, add the exact integer number of calendar days.
3. If lag unit is `business_days`, count the exact integer number of business days strictly after the anchor using the settlement calendar; the anchor itself is day zero.
4. Apply `settlement_business_day_convention` using the settlement calendar to the resulting lag date.
5. Preserve anchor date, lag unit/count, unadjusted lag result and final adjusted payment date.

Zero lag is explicit: the adjusted event date is the lag result, after which the settlement business-day convention is applied. Missing calendar data or unsupported date range MUST fail closed.

This rule does not introduce component-specific payment schedules. Alternative payment schedules or component-specific lags require a future language version.

## 6. Event model and total ordering

### 6.1 Event record

Every scheduled event MUST be immutable and typed. It MUST carry:
- event schema version and event kind;
- deterministic event ID;
- FIR contract hash;
- component identifier/path where applicable;
- observation index where applicable;
- nominal date, effective/adjusted date and payment date where applicable;
- priority rank for same-date contractual component events;
- references to immutable calendar and fixing inputs;
- typed event payload.

Unknown event kinds or event-schema versions MUST be rejected. The runtime MUST NOT silently ignore an event.

### 6.2 Event kinds

The PSL 1.0 runtime event vocabulary is:
`INITIAL_FIXING`, `OBSERVATION_FIXING`, `COUPON_EVALUATION`, `COUPON_PAYMENT`, `AUTOCALL_EVALUATION`, `AUTOCALL_REDEMPTION`, `MATURITY_EVALUATION`, `MATURITY_REDEMPTION`, `CASHFLOW_SETTLEMENT`.

No discretionary termination, issuer call, holder put, disruption-resolution, barrier-breach intraday or other unlisted event is defined by PSL 1.0.

### 6.3 Total order

Events are ordered by:
1. effective date ascending;
2. mandatory phase;
3. for contractual component phases on the same effective date, the exact `execution.same_date_priority` permutation;
4. observation index ascending where applicable;
5. stable component identifier;
6. deterministic event ID as final tie-breaker.

Mandatory phases:
- Phase 0: initial and observation fixing availability.
- Phase 1: contractual component processing, respecting the exact same-date priority permutation.
- Phase 2: settlement of already-created cashflow obligations.

Fixing events MUST precede every condition evaluation for the same effective date. Settlement MUST occur after the contractual obligation is created and MUST NOT re-evaluate payoff conditions. The same-date priority field MUST contain exactly one each of `coupon`, `autocall`, and `capital_redemption`; no YAML component order or implementation-specific sort may override it.

Within a component's priority slot, evaluation and any immediate contractual obligation creation are atomic for ordering purposes. The scheduler MUST NOT interleave another component between a component's evaluation and its associated redemption/payment creation.

## 7. Coupon memory, precedence and terminal behavior

A coupon evaluation is performed exactly once at its scheduled observation. It uses the complete fixing set for that observation and the coupon condition from FIR.

For a memory coupon:
- If the coupon condition is satisfied, the coupon obligation is the current period's accrued coupon plus all previously accumulated unpaid coupon memory. The memory balance is reset to zero once that obligation is created.
- If the condition is not satisfied, the current period's accrued coupon is added to unpaid coupon memory.
- Memory arithmetic uses exact decimal values. It MUST NOT round intermediate values because PSL 1.0 does not define a rounding stage. Accordingly, a contract requiring a rounding decision that affects accrual, accumulation or payment is not execution-eligible under §8.
- Coupon evaluation/payment obligation creation MUST NOT occur more than once for the same component and observation index.

The same-date priority permutation determines coupon/autocall interaction:
- If `coupon` precedes `autocall`, the coupon is evaluated first. If eligible, the current and memory coupon obligation is created and memory reset before autocall is evaluated. The autocall unpaid-coupon policy then applies only to any remaining unpaid memory.
- If `autocall` precedes `coupon` and autocall triggers, redemption is created and the product becomes terminal; the later coupon event is suppressed. If autocall does not trigger, processing continues to the coupon slot.
- If coupon is not eligible before autocall, its current accrual is added to memory; autocall's explicit `pay_all` or `forfeit` policy applies to the resulting unpaid memory.
- If autocall is terminal, all later contractual component events on that date and all future dates are suppressed. No later maturity redemption may be emitted.
- If maturity capital redemption is processed before an autocall event on the same date, maturity is terminal and the later autocall is suppressed. If autocall is processed first and triggers, maturity redemption is suppressed. This follows the declared priority order and prevents duplicate principal redemption.

The six permutations of the three priority labels are all valid inputs and MUST be tested. Their outcomes may differ because the contract explicitly selected different precedence; the runtime MUST preserve, not normalize, that order.

## 8. PSL 1.0 execution-ineligible semantics (reserved for PSL 1.1)

The following are not safely determined by the PSL 1.0 contract. The runtime MUST reject execution when the contract depends on them. Implementations MUST NOT choose a market convention or economic interpretation on behalf of the contract author.

| ID | Unresolved capability | PSL 1.0 treatment | PSL 1.1 proposal |
|---|---|---|---|
| U01 | Exact `30_360` day-count variant | Reject execution if selected | Add explicit variant (e.g. 30/360 US, 30E/360) |
| U02 | Exact first/last stub period construction | Reject execution if a stub is required | Define unadjusted period generation and short/long first/last algorithms |
| U03 | Coupon rounding stage relative to memory accumulation/payment | Reject execution if rounding affects coupon economics | Define accrual precision, per-period/final rounding stage and memory rounding |
| U04 | Principal cashflow rounding stage/fields | Reject execution if rounding is required but not specified by FIR | Define principal precision and rounding semantics |
| U05 | Independent underlying fixing calendars | Reject; use only the defined observation-date rule | Add fixing calendar and fixing-date convention per source/underlying |
| U06 | Per-currency quanto rates | Reject under existing single-rate restriction | Add typed per-currency rates and quote conventions |
| U07 | Alternative/component-specific payment schedules or lags | Reject unsupported schedule semantics | Add typed payment schedules and per-cashflow lag rules |
| U08 | Contractual market disruption, stale-price, missing-fixing or fallback hierarchy | Reject; no fallback | Add explicit disruption/fallback policy and precedence |
| U09 | Discretionary issuer/holder early termination | Reject unrecognized termination clauses | Add typed termination rights, triggers, notice and settlement rules |
| U10 | Additional contractual lifecycle events | Reject unknown event types | Add versioned event vocabulary and transitions |
| U11 | New schedule-generation conventions beyond §3 | Reject unsupported convention | Add explicitly named/versioned schedule conventions |
| U12 | New FX/performance transformations not represented in FIR 1.0 | Reject | Add typed transformations in PSL 1.1+ |

A PSL 1.0 contract using `30_360`, a required stub, or an economically material unspecified rounding stage MUST NOT be marked execution-eligible merely because the compiler accepts the corresponding enum/fields. This restriction does not alter compiler acceptance or the contract hash; it is a runtime eligibility gate.

## 9. Lifecycle state machine

### 9.1 States

- `PENDING`: FIR and immutable execution inputs have not completed preflight.
- `ACTIVE`: preflight succeeded; scheduled events may be reduced.
- `TERMINATED_AUTOCALL`: an eligible autocall has created its principal redemption obligation.
- `MATURED`: maturity redemption has been created.
- `FAILED`: technical/input/invariant failure; not a contractual termination.

### 9.2 Transitions

| Current state | Event/condition | Next state | Required effect |
|---|---|---|---|
| PENDING | All preflight checks pass | ACTIVE | Freeze run input references |
| PENDING | Any preflight check fails | FAILED | Emit diagnostic; no contractual cashflow |
| ACTIVE | Nonterminal valid event | ACTIVE | Reduce event exactly once |
| ACTIVE | Triggered autocall redemption | TERMINATED_AUTOCALL | Create principal obligation once; stop later contractual events |
| ACTIVE | Maturity redemption | MATURED | Create principal obligation once; stop later contractual events |
| ACTIVE | Missing/conflicting fixing, invalid transition, unknown event, invariant failure | FAILED | Stop run; do not manufacture a contractual termination |
| TERMINATED_AUTOCALL | Any later contractual event | No transition | Reject/suppress as post-terminal |
| MATURED | Any later contractual event | No transition | Reject/suppress as post-terminal |
| FAILED | Any event | No transition | Reject; failed run is immutable |

PSL 1.0 has no generic discretionary early-termination transition. Autocall is the only early contractual termination represented by the current PSL 1.0 vocabulary. `FAILED` MUST never be represented as `TERMINATED_AUTOCALL` or `MATURED`.

### 9.3 Terminal short-circuit

After transition to `TERMINATED_AUTOCALL` or `MATURED`, no later contractual component event may create a coupon, principal redemption or additional lifecycle transition. Previously created cashflow obligations may still be settled in Phase 2 on their scheduled payment dates. Settlement of an existing obligation does not reopen the product or re-evaluate economics.

## 10. Event identity, idempotency and replay

Event IDs MUST be deterministic and derived from a canonical tuple containing at least:
- contract hash;
- event schema version and event kind;
- component identifier (or a fixed contract-level identifier);
- observation index (or explicit null);
- nominal, effective and payment dates (explicit null where not applicable);
- calendar bundle hash;
- fixing snapshot hash when the event depends on fixings.

The tuple MUST be serialized as canonical UTF-8 JSON using sorted object keys, compact separators, ISO dates, explicit nulls and canonical decimal strings, then hashed with SHA-256. UUIDs, timestamps, random values, hostnames and process-local counters MUST NOT participate.

Idempotency rules:
- Reprocessing an event ID with byte-for-byte identical canonical event content is an idempotent replay and MUST NOT duplicate state changes or cashflows.
- Reprocessing an event ID with different canonical content is an identity collision and MUST fail the run.
- A distinct event ID that attempts to repeat an already-consumed contractual action for the same component/observation MUST fail as a duplicate action.
- Replay MUST use the exact same FIR, calendar and fixing snapshot hashes. Different input hashes constitute a different run, not a replay.

The runtime MUST expose enough trace information to explain event identity, ordering, reduction result and any rejected duplicate.

## 11. Cashflow and trace requirements

Every emitted cashflow MUST have a stable cashflow ID, type, currency, exact decimal amount, contractual event date, payment date, originating event ID and component reference. Cashflow creation is immutable. Settlement changes settlement status only; it MUST NOT recompute the amount.

The lifecycle trace MUST record:
- run and input artifact hashes;
- prior and next lifecycle state;
- event ID/kind, effective date and ordering key;
- fixing references used by the event;
- component condition result;
- coupon memory before/after;
- cashflow IDs created;
- diagnostic/rejection reason where applicable.

No binary floating-point arithmetic is permitted for contractual amounts, thresholds, memory balances or cashflow values. Use exact decimal/rational operations as appropriate. A downstream pricing engine may use floating-point numerical methods, but it MUST consume the already-defined contractual cashflow semantics.

## 12. Stable diagnostics

At minimum, runtime diagnostics MUST have stable machine-readable codes for:
- unsupported PSL/FIR/event schema version;
- FIR schema/hash mismatch;
- execution-ineligible PSL 1.0 feature;
- missing calendar/calendar hash mismatch/date outside range;
- schedule collision;
- missing/duplicate/conflicting fixing;
- incomplete basket;
- unsupported fixing-date rule;
- unknown event kind;
- invalid lifecycle transition/post-terminal event;
- duplicate action/event identity collision;
- non-deterministic or inconsistent replay input.

Diagnostic records MUST include severity, code, message, contract/component path where applicable, effective/nominal date where applicable and input reference. No contractual cashflow may be emitted after a fail-closed error.

## 13. Normative evidence and relationship to PSL 1.0 source

This companion contract is grounded in the following existing normative requirements:
- PSL 1.0 §1: no undocumented defaults; undefined material terms are execution errors; no executable FPIR on errors.
- PSL 1.0 §5: explicit initial fixing source/date, exact normalized performance formula and explicit FX treatment.
- PSL 1.0 §6: schedule anchored at first observation; named calendar and business-day convention; deterministic dates; no calendar substitution; runtime calendar/version/range/collision/EOM obligations.
- PSL 1.0 §7: explicit coupon accrual/day-count/payment/stub/rounding; explicit same-date precedence; autocall redemption and unpaid coupon treatment; maturity redemption including equality; no product-specific inferred economics.
- PSL 1.0 §9 and §12: contract hash coverage, version compatibility, no silent reinterpretation, independent FIR versioning.
- PSL 1.0 §14: typed closed-schema execution fields and explicit event priority, settlement calendar and payment lag.

Where the source specification names a field but does not determine its economic interpretation (notably `30_360`, stubs and rounding stage), §8 is a restriction on runtime execution, not an invented interpretation.

## 14. SFI-11 acceptance gate

SFI-11 is acceptable only when all of the following are true:

1. This contract is reviewed and accepted as the normative runtime companion to PSL 1.0.
2. The machine-readable conformance vectors in `tests/conformance/psl_1_0_runtime_vectors.json` are versioned and independently executable.
3. The conformance runner validates every vector and its expected outcome; all six same-date permutations are covered.
4. Positive vectors cover anchored EOM/non-EOM schedules, settlement lag, phase ordering, stable event identity and valid lifecycle transitions.
5. Negative vectors cover collisions, unsupported calendar ranges, missing/duplicate/conflicting fixings, partial baskets, post-terminal events, identity collisions and all §8 execution-ineligible features.
6. Vector failures identify a stable vector ID and rule ID.
7. Tests require no production runtime implementation; the reference oracle exists solely to verify the published examples and normative expected outcomes.
8. The contract and vectors are linked from SFI-11 and CI.
9. No production runtime implementation begins until the user/architect explicitly accepts the specification gate.

Passing this gate approves the specification and test contract only. It does not mark SFI-11 implemented, nor authorize SFI-12–15 implementation without their own approved contracts.
