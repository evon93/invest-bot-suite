import random
import time
from typing import List, Dict, Any, Optional
from contracts.event_messages import OrderIntent, ExecutionReport
import math

def simulate_execution(
    intents: List[OrderIntent],
    cfg: Dict[str, Any],
    seed: int = 42
) -> List[ExecutionReport]:
    """
    Simulates execution for a list of OrderIntents in a deterministic, live-like manner.
    
    Args:
        intents: List of OrderIntent objects.
        cfg: Configuration dictionary (slippage_bps, partial_fill, avg_latency_ms).
        seed: Random seed for reproducibility.
        
    Returns:
        List[ExecutionReport]
    """
    rng = random.Random(seed)
    reports = []
    
    slippage_bps = cfg.get('slippage_bps', 5.0)
    avg_latency_ms = cfg.get('avg_latency_ms', 100.0)
    partial_fill_enabled = cfg.get('partial_fill', False)
    
    for intent in intents:
        # 1. Latency Simulation
        # LogNormal distribution often models latency well
        # varying slightly around avg
        latency_noise = rng.gauss(0, avg_latency_ms * 0.2)
        latency_ms = max(0.0, avg_latency_ms + latency_noise)
        
        # 2. Price Determination
        # Try to find a reference price (market price at arrival)
        # In a real backtest, this comes from the engine or data stream.
        # Here, we look for 'current_price' or 'close' in meta, or fallback to limit_price (if set),
        # or error/placeholder if strictly unknown.
        ref_price = intent.meta.get('current_price') or intent.meta.get('close') or intent.limit_price
        
        if ref_price is None:
            # Fallback if no price context: assume 100.0 for simulation if allowed, 
            # or skip/reject. Let's assume 100.0 with a warning meta to unblock simulation flows
            # unless strict mode.
            ref_price = 100.0 
        
        # 3. Slippage
        # Buy: price goes UP (+), Sell: price goes DOWN (-) normally implies worse execution?
        # Actually:
        # Buy: Fill Price > Ref Price (Paying more) -> Slippage positive effect on cost (bad)
        # Sell: Fill Price < Ref Price (Receiving less) -> Slippage negative impact
        
        # We model slippage_bps as "cost penalty".
        # Buy: fill = ref * (1 + slip)
        # Sell: fill = ref * (1 - slip)
        
        # We create some variance in slippage too
        actual_slippage_bps = rng.gauss(slippage_bps, slippage_bps * 0.5)
        # Clamp to reasonable range (e.g., min 0, or allow negative/positive slippage?)
        # Let's allow strictly positive penalty for "live-like conservative" simulation.
        actual_slippage_bps = max(0.0, actual_slippage_bps)
        
        if intent.side.upper() == 'BUY':
            fill_price = ref_price * (1 + actual_slippage_bps / 10000.0)
        else:
            fill_price = ref_price * (1 - actual_slippage_bps / 10000.0)
            
        # 4. Fills logic
        remaining_qty = intent.qty
        
        fills = []
        if partial_fill_enabled and remaining_qty > 0:
            # Split into 2-3 fills
            splits = rng.randint(2, 3)
            chunk = remaining_qty / splits
            # Randomize chunks slightly
            for i in range(splits - 1):
                # variance +/- 20%
                var = rng.uniform(0.8, 1.2)
                this_fill = chunk * var
                this_fill = min(this_fill, remaining_qty)
                this_fill = round(this_fill, 6) # Rounding to avoids weird floats
                if this_fill > 0:
                    fills.append(this_fill)
                    remaining_qty -= this_fill
            
            # Last fill takes remainder
            if remaining_qty > 0:
                fills.append(round(remaining_qty, 6))
        else:
            fills = [intent.qty]
            
        # Generate Reports
        for i, qty in enumerate(fills):
            status = "FILLED"
            if partial_fill_enabled and len(fills) > 1:
                status = "PARTIALLY_FILLED" if i < len(fills) - 1 else "FILLED"
            
            # Simple Fee model: 0.1% or similar
            fee_rate = 0.001
            fee = (qty * fill_price) * fee_rate
            
            rep = ExecutionReport(
                ref_order_event_id=intent.event_id,
                status=status,
                filled_qty=qty,
                avg_price=fill_price,
                fee=fee,
                slippage=actual_slippage_bps,
                latency_ms=latency_ms,
                extra={
                    "simulated": True,
                    "ref_price": ref_price,
                    "fill_seq": i+1,
                    "total_fills": len(fills)
                }
            )
            reports.append(rep)
            
    return reports
