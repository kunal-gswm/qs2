import json
import hashlib
from typing import Any, Dict

def _normalize_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        # Round to a sensible precision to avoid float variance across architectures
        return round(obj, 10)
    elif isinstance(obj, dict):
        return {k: _normalize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_floats(x) for x in obj]
    else:
        return obj

def generate_config_hash(config_dict: Dict[str, Any], cost_dict: Dict[str, Any]) -> str:
    """
    Generates a canonical SHA-256 hash of the full strategy configuration.
    Requires sorted keys, normalized floats, and UTF-8 encoding.
    """
    combined = {
        "strategy": config_dict,
        "costs": cost_dict
    }
    
    normalized = _normalize_floats(combined)
    canonical_json = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

if __name__ == "__main__":
    from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, to_dict
    
    strat_dict = to_dict(BASELINE_CONFIG)
    cost_dict = to_dict(INDIA_EQUITY_DELIVERY_2026_09)
    
    config_hash = generate_config_hash(strat_dict, cost_dict)
    print(f"Frozen Configuration Hash: {config_hash}")
