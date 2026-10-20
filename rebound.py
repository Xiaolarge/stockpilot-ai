"""Transparent oversold rebound candidate and conditional trading plan, daily bars only."""
import math
import numpy as np
from engine import indicators
from fees import net_result, size_with_fees

US = ['NVDA','AMD','MU','INTC','ARM','TSLA','AMZN','GOOGL','META','AVGO','PLTR','ADBE','QCOM','LRCX','AMAT','QQQM']
JP = ['9984.T','285A.T','7735.T','8035.T','6857.T','6920.T','7203.T','6758.T','7974.T','6501.T','4063.T','6098.T','8306.T','9432.T']

def rebound_plan(symbol, df, account=650, risk_pct=1.0, lot=1, max_days=10, min_turnover=2e6, buy_fee=0.38, sell_fee=0.38):
    x=indicators(df)
    if len(x)<90: raise ValueError('需要至少90个交易日数据')
    p=x.iloc[-1]; prev=x.iloc[-2]
    price=float(p.Close); atr=float(p.ATR14)
    if not np.isfinite(price) or price<=0 or not np.isfinite(atr) or atr<=0: raise ValueError('价格或ATR无效')
    close=x.Close
    peak20=float(close.tail(21).max())
    drawdown=(price/peak20-1)*100
    rsi=float(p.RSI14)
    prev_rsi=float(prev.RSI14)
    volratio=float(p.Volume/p.VOL20) if p.VOL20>0 else 0
    rebound=price>float(p.EMA20) and rsi>prev_rsi and rsi>=35 and volratio>=1.2
    recently_oversold=bool((x.RSI14.tail(12)<35).any())
    deep_drop=bool((close/close.rolling(20).max()-1).tail(12).min()<=-.10)
    turnover=float(p.Volume)*price
    liquid=turnover>=min_turnover
    # Gap risk: conditional entry band uses known latest close and ATR, not a future fill.
    entry_low=max(.01,price-.35*atr)
    entry_high=price+.15*atr
    stop=min(float(p.SUPPORT20),price-1.5*atr)
    risk_per_share=entry_high-stop
    resistance=float(p.RESIST20)
    target=max(resistance,entry_high+2*risk_per_share)
    rr=(target-entry_high)/risk_per_share if risk_per_share>0 else 0
    score=(25 if deep_drop else 0)+(20 if recently_oversold else 0)+(20 if rebound else 0)+(15 if volratio>=1.5 else (8 if volratio>=1.2 else 0))+(10 if liquid else 0)+(10 if rr>=2 else 0)
    if not liquid: status='流动性不足，排除'
    elif not deep_drop: status='尚未满足近期急跌条件'
    elif rebound and recently_oversold: status='反弹初步确认，等待价格条件'
    else: status='超跌观察，尚未确认反弹'
    shares_by_risk=math.floor(account*risk_pct/100/risk_per_share) if risk_per_share>0 else 0
    shares_by_cash=math.floor(account/entry_high/lot)*lot if entry_high>0 else 0
    shares=size_with_fees(account,risk_pct,entry_high,stop,lot,buy_fee,sell_fee)
    trade=net_result(entry_high,target,shares,buy_fee,sell_fee)
    breakeven=entry_high+(buy_fee+sell_fee)/shares if shares else None
    net_rr=(trade["net"] / (shares*risk_per_share+buy_fee+sell_fee)) if shares else 0
    return {'代码':symbol,'日期':str(x.index[-1].date()),'币种':'JPY' if symbol.endswith('.T') else 'USD',
            '收盘价':round(price,2),'近20日高点回撤%':round(drawdown,2),'RSI':round(rsi,1),'量比':round(volratio,2),
            '反弹评分':score,'状态':status,'观察入场下沿':round(entry_low,2),'观察入场上沿':round(entry_high,2),
            '参考止损':round(stop,2),'参考止盈':round(target,2),'计划持有交易日':max_days,
            '风险收益比':round(rr,2),'参考股数':shares,'计划风险金额':round(shares*risk_per_share,2),
            '成交额':round(turnover,0),'买入手续费':buy_fee,'卖出手续费':sell_fee,
            '往返手续费':round(buy_fee+sell_fee,4),'保本卖价':round(breakeven,4) if breakeven else None,
            '目标净利润':round(trade['net'],2) if shares else None,'目标净收益率%':round(trade['net_pct'],2) if shares else None,
            '扣费后风险收益比':round(net_rr,2)}
