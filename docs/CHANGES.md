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
