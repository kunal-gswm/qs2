import math
from bveqse.config import StrategyConfig
from bveqse.backtest.costs import calculate_leg_costs

def calculate_position_size(
    equity: float,
    available_cash: float,
    f_entry: float,
    r_per_share: float,
    median_traded_value: float,
    config: StrategyConfig,
    fee_buffer_kappa: float = 0.005
) -> int:
    """
    Calculates the position size based on PRD Section 8.2 Position Sizing.
    q = min(qrisk, wmax*Eq / F, padv*Vmed / F, Cash / F(1+kappa))
    """
    if equity <= 0 or available_cash <= 0:
        return 0
        
    risk_amount = config.risk_fraction_f * equity
    
    if r_per_share <= 0:
        return 0
        
    q_risk = risk_amount / r_per_share
    
    w_max_shares = (config.max_weight * equity) / f_entry
    
    p_adv_shares = (config.adv_participation_cap * median_traded_value) / f_entry
    
    cash_shares = available_cash / (f_entry * (1.0 + fee_buffer_kappa))
    
    q = min(q_risk, w_max_shares, p_adv_shares, cash_shares)
    
    # Must be whole shares
    return math.floor(q)
