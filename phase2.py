"""Phase 2: point-in-time signal backtest, stock ranking, and financial summaries."""
import math
import numpy as np
import pandas as pd
from engine import indicators, classify

CORE = ['NVDA','GOOGL','AMZN','AMD','MSFT','AVGO','AAPL','META','TSLA','COST','NFLX','ADBE','INTC','MU','AMAT','LRCX','PANW','CRWD','PLTR','CSCO','QCOM','INTU','BKNG','PEP','TXN','ADI','ISRG','MELI','SHOP','QQQM']

def clean_number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def scan_one(symbol, df):
    x = indicators(df)
    if len(x) < 90:
        raise ValueError('历史日线不足90根')
    x['STATE'] = x.apply(classify, axis=1)
    r = x.iloc[-1]
    price = float(r.Close)
    if price <= 0 or not np.isfinite(price):
        raise ValueError('收盘价无效')
    volratio = clean_number(r.Volume / r.VOL20) if r.VOL20 > 0 else None
    atrpct = clean_number(100 * r.ATR14 / price)
    trend = 25 if r.EMA20 > r.EMA60 and price > r.EMA20 else (12 if price > r.EMA20 else 0)
    momentum = 20 if r.MACD_HIST > 0 and 45 <= r.RSI14 <= 70 else (10 if r.MACD_HIST > 0 else 0)
    volume = 15 if volratio is not None and volratio >= 1.2 else (8 if volratio is not None and volratio >= .8 else 0)
    volatility = 15 if atrpct is not None and 1.5 <= atrpct <= 5 else (7 if atrpct is not None and .7 <= atrpct <= 8 else 0)
    liquidity = 15 if r.Volume * price >= 50_000_000 else (7 if r.Volume * price >= 10_000_000 else 0)
    risk = 10 if r.RSI14 < 70 and price > r.EMA20 else 0
    score = trend + momentum + volume + volatility + liquidity + risk
    state = str(r.STATE)
    action = '候选观察' if state == '上涨确认' and score >= 65 else '等待确认'
    return {'代码':symbol,'数据日期':str(x.index[-1].date()),'收盘价$':round(price,2), '波段状态':state,
            '评分/100':score,'成交量比':round(volratio,2) if volratio is not None else None,
            'ATR%':round(atrpct,2) if atrpct is not None else None,'RSI':round(float(r.RSI14),1),
            '观察结论':action}

def backtest(df, starting_cash=650, risk_pct=1, fee=0, slippage_bps=10, atr_multiple=2,
             max_bars=15, allow_fractional=False):
    """Daily close signal -> NEXT open entry; next-open exits for signal/timeout.
    Stop uses next-day OHLC; gap opens fill at opening price. One position max.
    Adjusted OHLC is a research proxy, not executable historical quotes.
    """
    x = indicators(df)
    if len(x) < 95:
        raise ValueError('回测至少需要95根日线')
    x['STATE'] = x.apply(classify, axis=1)
    cash = float(starting_cash)
    trades = []
    equity = [{'日期':str(x.index[0].date()),'权益$':cash}]
    position = None
    slip = slippage_bps / 10000
    for i in range(90, len(x)):
        row = x.iloc[i]
        prev = x.iloc[i-1]
        date = str(x.index[i].date())
        if position is not None:
            exit_price = None
            reason = None
            # Prior close signal is only actionable at today's open.
            if prev.STATE != '上涨确认':
                exit_price, reason = float(row.Open)*(1-slip), '前收盘趋势失效'
            elif i-position['entry_i'] >= max_bars:
                exit_price, reason = float(row.Open)*(1-slip), '达到最大持有期'
            elif float(row.Open) <= position['stop']:
                exit_price, reason = float(row.Open)*(1-slip), '跳空触发止损'
            elif float(row.Low) <= position['stop']:
                exit_price, reason = position['stop']*(1-slip), '日内触发止损'
            if exit_price is not None:
                cash += position['shares']*exit_price-fee
                pnl = position['shares']*(exit_price-position['entry_price'])-2*fee
                trades.append({'入场日':position['date'],'出场日':date,'入场价$':round(position['entry_price'],3),
                               '出场价$':round(exit_price,3),'股数':position['shares'], '净盈亏$':round(pnl,2),
                               '净收益率%':round(pnl/(position['shares']*position['entry_price']+fee)*100,2),
                               '原因':reason})
                position = None
        # Entries use yesterday's close state; today's open for fills.
        if position is None and prev.STATE == '上涨确认' and x.iloc[i-2].STATE != '上涨确认':
            entry = float(row.Open)*(1+slip)
            stop = min(float(prev.SUPPORT20), float(prev.Close)-atr_multiple*float(prev.ATR14))
            risk_per_share = entry-stop
            if np.isfinite(risk_per_share) and risk_per_share > 0 and entry > 0:
                by_risk = cash*risk_pct/100/risk_per_share
                by_cash = max(0,(cash-fee)/entry)
                shares = min(by_risk,by_cash)
                if not allow_fractional:
                    shares = math.floor(shares)
                if shares > 0:
                    cash -= shares*entry+fee
                    position = {'entry_i':i,'date':date,'entry_price':entry,'stop':stop,'shares':shares}
                    # Conservative same-day stop handling when low crosses stop.
                    if float(row.Low) <= stop:
                        exit_px = (float(row.Open) if float(row.Open) <= stop else stop)*(1-slip)
                        cash += shares*exit_px-fee
                        pnl = shares*(exit_px-entry)-2*fee
                        trades.append({'入场日':date,'出场日':date,'入场价$':round(entry,3),'出场价$':round(exit_px,3),
                                       '股数':shares,'净盈亏$':round(pnl,2),
                                       '净收益率%':round(pnl/(shares*entry+fee)*100,2),'原因':'入场当日触发止损'})
                        position = None
        value = cash + (position['shares']*float(row.Close) if position else 0)
        equity.append({'日期':date,'权益$':round(value,2)})
    # Open position is mark-to-market only, not treated as a realized trade.
    curve = pd.DataFrame(equity)
    deals = pd.DataFrame(trades)
    total = len(deals)
    wins = int((deals['净盈亏$'] > 0).sum()) if total else 0
    maxdd = float((curve['权益$']/curve['权益$'].cummax()-1).min()*100)
    return deals, curve, {'已平仓次数':total,'胜率%':round(wins/total*100,2) if total else None,
                          '期末权益$':round(float(curve['权益$'].iloc[-1]),2),
                          '总收益率%':round((float(curve['权益$'].iloc[-1])/starting_cash-1)*100,2),
                          '最大回撤%':round(maxdd,2),'持仓未平仓':position is not None}

def summarize_financials(info, income, earnings_dates=None):
    """Never fabricate missing accounting data; metadata may be stale."""
    keys = {'公司名称':'longName','市值$':'marketCap','市盈率(TTM)':'trailingPE',
            '预期市盈率':'forwardPE','营收同比增长':'revenueGrowth','利润同比增长':'earningsGrowth',
            '营业利润率':'operatingMargins','自由现金流$':'freeCashflow','总负债$':'totalDebt',
            '现金$':'totalCash','下期预期EPS':'forwardEps','过去EPS':'trailingEps'}
    rows = [{'指标':label,'数值':info.get(k),'数据字段':k} for label,k in keys.items()]
    return pd.DataFrame(rows)
