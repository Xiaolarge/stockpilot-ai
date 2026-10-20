"""Fixed per-order fee accounting; fees are in the same currency as the trade."""
import math

def net_result(buy, sell, shares, buy_fee=0.38, sell_fee=0.38):
    if min(buy, sell, shares, buy_fee, sell_fee) < 0:
        raise ValueError('价格、股数、手续费不能为负数')
    gross=(sell-buy)*shares
    fees=buy_fee+sell_fee if shares else 0
    invested=buy*shares+buy_fee if shares else 0
    net=gross-fees
    return {'gross':gross,'fees':fees,'net':net,'net_pct':100*net/invested if invested else 0,
            'break_even':buy+(fees/shares) if shares else None}

def size_with_fees(cash, risk_percent, entry, stop, lot=1, buy_fee=0.38, sell_fee=0.38):
    if cash<=0 or entry<=0 or stop>=entry or lot<1 or risk_percent<=0: return 0
    total_fee=buy_fee+sell_fee
    cash_lots=math.floor(max(0,cash-buy_fee)/(entry*lot))
    risk_budget=cash*risk_percent/100
    risk_lots=math.floor(max(0,risk_budget-total_fee)/((entry-stop)*lot))
    return max(0,min(cash_lots,risk_lots))*lot
