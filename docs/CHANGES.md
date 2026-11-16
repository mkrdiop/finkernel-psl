# Correctifs issus de la revue de code (v1 → v1.1)

Référence : revue de `finkernel_v1_blueprint.zip` par rapport à `FINKERNEL_development_blueprint.docx`.
Suite de tests : 102 tests (unitaires, compilateur, golden, property-based).

## 1. Bloquants
| Problème | Correction |
|---|---|
| `NameError: Tuple_Result` (double `compile_yaml`) | Stub supprimé; `PSLCompiler.compile()` + `compile_yaml()` de compatibilité |
| `QuantLib-Python>=1.34` introuvable (PyPI s'arrête à 1.18) | Extra `quant` avec `QuantLib>=1.34`; dépendances du cœur réduites à pydantic + PyYAML |
| `pytest` ne collecte rien sans installation | `pythonpath` dans `pyproject.toml`; `__init__.py` partout; `packages.find` sur `src/` |

## 2. Hash et FIR (§4.6, ADR-002, ADR-003)
- `contract_hash` ne couvre plus que le contrat. `valuation_hash` et `risk_hash` sont distincts.
- Ajout au hash des termes oubliés : `settlement` (devise, délai, unité), `category`, devise du notionnel.
- Collections non significatives triées (sous-jacents, panier). Ordre des composants conservé (potentiellement significatif).
- Montants en `Decimal` → chaîne canonique (`100000.00` ≡ `100000` ≡ `1e5`); `float` interdit dans le contenu canonique.
- SHA-256 complet (64 hex) au lieu de 16; `source_hash` de la spécification (fins de ligne normalisées).
- FIR structurée : `product / terms / underlyings / reference / observation_schedule / components`, plus `provenance`
  (`compilation_id`, `compiled_at`, versions compilateur/PSL/FIR, `source_hash`). Horloge et générateur d'ID injectables.

## 3. Pipeline et diagnostics (§4.1–4.5)
- AST entièrement typé (plus de `Dict` ni de `raw_config`) : dates `date`, montants `Decimal`, enums fermés.
- Étapes : parser → AST/type checker → validateur sémantique → validateur contractuel → normaliseur → FIR → hash.
- Diagnostics structurés (code, sévérité, chemin, ligne/colonne), erreurs bloquantes distinctes des avertissements, toutes
  rapportées en une passe. Les erreurs utilisateur ne sont plus des « Internal Compiler Error ».

## 4. Entrées invalides désormais rejetées
Dates invalides / non ISO / ordre (y compris `2027-1-5`), dates non quotées (acceptées), notionnel ≤ 0, devise du notionnel,
devises hors vocabulaire, seuils/taux hors domaine (700 %), calendriers/fréquences/types/agrégations inconnus, identifiants
dupliqués, panier dupliqué ou non déclaré, `start_observation` hors calendrier, autocall sans terminaison, composant
manquant (branche indéfinie), barrière de capital > seuil d'autocall, **champs inconnus** (fautes de frappe), valeurs
YAML mal typées. Parseur : alias/ancres, clés non-chaînes, `NO`→faux, `010`→8, `1e3`→float, dates→`datetime` neutralisés.

## 5. Phoenix : lacunes de spécification (signalées en avertissements, pas encore résolues)
`W-REF-PERFORMANCE-UNSPECIFIED` (pas de strike/fixing initial), `W-FX-UNSPECIFIED` (sous-jacents USD/JPY, produit EUR),
`W-SAME-DATE-ORDER-UNSPECIFIED` (ordre coupon/autocall/remboursement). Restent aussi à définir : proratisation du coupon,
day count, montant versé à l'autocall, formule de remboursement sous la barrière, calendrier de `payment_lag`.

## Changements d'API (cassants, internes)
- `parse_yaml_strict()` retourne `ParsedDocument(data, source_map)`.
- `validate_semantics(ast, bag)` écrit dans un `DiagnosticBag` (plus de `List[str]`).
- `psl_version` est obligatoire; `risk` doit être un mapping `{measures: [...]}`.
- `FIRModel` remplacé par `FIRDocument` (accesseurs `product_id`, `canonical_hash`, `compiled_at`, `underlyings`, `components` conservés).

## Reste à faire (hors périmètre de ce patch)
Génération d'événements (`events`), calendriers/jours ouvrés, runtime et cashflows, exemples Reverse Convertible et Swap
(+ leurs types de composants), schéma JSON versionné de FIR (`schemas/fir/v1`), CI, ADR, API.


## 2026-11-16 — M1 PSL 1.0 execution contract and compiler gate

- Published `docs/PSL_1.0_SPEC.md` as the normative language contract and linked it from the README.
- Added mandatory typed `execution` terms to the PSL AST. The compiler now fails closed for missing/unknown execution fields, invalid dates and enums, unsupported product subtypes, implicit coupon-memory behavior, invalid FX/quanto declarations, and incomplete event/redemption terms.
- Defined normalized underlying performance as `price_over_initial` (a ratio, not a return percentage). FX conversion explicitly declares initial/observation fixing rule, source and quote convention; quanto declares a fixed positive rate and quote convention; local-currency performance is an explicit third mode.
- Made coupon accrual start, day count, payment date, stub and rounding conventions explicit. Same-date event precedence is a complete permutation; autocall and maturity redemption rules are explicit.
- Removed the untyped `reference.performance` mapping. Execution semantics are now located only at `execution.performance`.
- Added strict Pydantic execution AST models and typed canonical FIR execution nodes. Execution terms are part of FIR contract content and therefore affect `contract_hash`; valuation/risk hashes remain independent.
- Published `schemas/psl/v1/psl.schema.json` and `schemas/fir/v1/fir.schema.json`, including discriminated FIR payoff components.
- Updated the Phoenix reference fixture and canonical FIR 1.0 golden contract/hash. Added negative, schema-conformance, hash-sensitivity and typed-FIR tests.
- Added GitHub Actions compiler CI across Python 3.10, 3.11 and 3.12. The M1 gate runs unit/compiler/schema/golden/property suites; legacy runtime tests remain outside this gate because M2 is not authorized and the existing runtime test fixture targets an obsolete PSL shape.
- First CI attempt exposed the runtime test's undeclared NumPy import; CI was scoped to the compiler quality gate rather than hiding or weakening that test. Latest M1 CI run #43873085428 passed across Python 3.10, 3.11 and 3.12: 124 tests passed on each version.

**M2 remains blocked** until the M1 PR is reviewed, all three Python CI jobs pass on the latest commit, and the PSL/FIR contracts are accepted.
