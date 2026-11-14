"""Constantes de domaine du PSL 1.0 (bornes de plausibilité et vocabulaire de référence)."""
from decimal import Decimal

from finkernel.psl.types.financial_types import Aggregation, ComponentType

# Seuils/barrières exprimés en fraction du niveau initial. > 200 % est presque
# certainement une erreur d'unité (ex. 70 au lieu de 0.70).
MAX_RATIO = Decimal("2")
# Coupon annuel exprimé en fraction (0.10 = 10 %). > 100 % : erreur d'unité probable.
MAX_ANNUAL_RATE = Decimal("1")
MAX_PAYMENT_LAG = 30

# Nom de la référence de performance attendue pour chaque agrégation.
REFERENCE_FOR_AGGREGATION = {
    Aggregation.WORST_OF: "worst_of_performance",
    Aggregation.BEST_OF: "best_of_performance",
}

# Composants requis (exactement une fois chacun) par sous-type de produit.
REQUIRED_COMPONENTS = {
    "phoenix_autocallable": (
        ComponentType.MEMORY_COUPON,
        ComponentType.AUTOCALL,
        ComponentType.CONDITIONAL_CAPITAL_PROTECTION,
    ),
}
