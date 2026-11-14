import hashlib
from typing import Any

from finkernel.fir.canonicalizer import canonical_json


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_canonical_hash(obj: Any) -> str:
    """SHA-256 complet (64 hex) de la forme canonique de ``obj``."""
    return sha256_text(canonical_json(obj))
