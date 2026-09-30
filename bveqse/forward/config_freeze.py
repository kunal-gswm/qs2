import json
import hashlib
from typing import Dict, Any
from dataclasses import asdict

from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09
from bveqse.data.universe import INTENDED_SYMBOLS

FORWARD_PARAMS = {
    'rho': 0.075,
    'L': 15,
    'mu_v': 2.0,
    'k': 1.25,
    'm': 3.0
}

def get_frozen_config_dict() -> Dict[str, Any]:
    # Baseline + Walk-forward selected parameters for the final fold
    cfg_dict = asdict(BASELINE_CONFIG)
    cfg_dict['range_threshold_rho'] = FORWARD_PARAMS['rho']
    cfg_dict['consolidation_lookback_L'] = FORWARD_PARAMS['L']
    cfg_dict['volume_multiple_mu'] = FORWARD_PARAMS['mu_v']
    cfg_dict['stop_atr_multiple_k'] = FORWARD_PARAMS['k']
    cfg_dict['target_r_multiple_m'] = FORWARD_PARAMS['m']
    # Serialize dates
    cfg_dict['history_start'] = cfg_dict['history_start'].isoformat()
    return cfg_dict

def get_frozen_cost_dict() -> Dict[str, Any]:
    c_dict = asdict(INDIA_EQUITY_DELIVERY_2026_09)
    c_dict['effective_date'] = c_dict['effective_date'].isoformat()
    c_dict['verification_date'] = c_dict['verification_date'].isoformat()
    return c_dict

def generate_config_hash() -> str:
    combined = {
        "strategy": get_frozen_config_dict(),
        "costs": get_frozen_cost_dict(),
        "universe": sorted(INTENDED_SYMBOLS)
    }
    json_str = json.dumps(combined, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

def verify_config_integrity(expected_hash: str) -> bool:
    return generate_config_hash() == expected_hash

if __name__ == "__main__":
    print(generate_config_hash())
