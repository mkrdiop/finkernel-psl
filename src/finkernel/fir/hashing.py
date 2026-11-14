import hashlib
import json
from typing import Dict, Any

def compute_canonical_hash(fir_body: Dict[str, Any]) -> str:
    canonical_json = json.dumps(fir_body, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()[:16]
