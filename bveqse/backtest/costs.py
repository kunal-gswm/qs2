from bveqse.config import CostConfig

def calculate_leg_costs(fill_price: float, quantity: int, is_buy: bool, cost_config: CostConfig) -> float:
    """
    Calculate full transaction costs for a single leg (buy or sell)
    based on the frozen CostConfig.
    """
    turnover = fill_price * quantity
    
    # Brokerage
    brokerage = turnover * cost_config.brokerage_rate
    if cost_config.brokerage_cap_inr > 0:
        brokerage = min(brokerage, cost_config.brokerage_cap_inr)
        
    # STT
    stt = turnover * cost_config.stt_rate
    
    # Exchange Transaction Charge
    exchange_charge = turnover * cost_config.exchange_transaction_charge_rate
    
    # SEBI Fee
    sebi_fee = turnover * cost_config.sebi_turnover_fee_rate
    
    # Stamp Duty (Buy leg only)
    stamp_duty = (turnover * cost_config.stamp_duty_rate) if is_buy else 0.0
    
    # GST (on brokerage + exchange charge + SEBI fee)
    gst = (brokerage + exchange_charge + sebi_fee) * cost_config.gst_rate
    
    # DP Charge (Sell leg only)
    # Applying GST to DP charge as is standard practice
    dp_charge = 0.0
    if not is_buy:
        dp_charge = cost_config.dp_charge_per_sell_inr * (1.0 + cost_config.gst_rate)
        
    total_cost = brokerage + stt + exchange_charge + sebi_fee + stamp_duty + gst + dp_charge
    return total_cost
