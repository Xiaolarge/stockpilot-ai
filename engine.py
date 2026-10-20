"""StockPilot AI: transparent, rule-based swing analysis. Educational use only."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class Settings:
    account: float = 650.0
    risk_pct: float = 1.0
    atr_multiple: float = 2.0
    min_rr: float = 2.0

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_index()
    for c in ('Open', 'High', 'Low', 'Close', 'Volume'):
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna(subset=['Open', 'High', 'Low', 'Close'])
    close = x['Close']
    x['EMA20'] = close.ewm(span=20, adjust=False).mean()
    x['EMA60'] = close.ewm(span=60, adjust=False).mean()
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    x['RSI14'] = (100 - 100/(1+rs)).where(down.ne(0), 100)
    x['MACD'] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    x['MACD_SIGNAL'] = x['MACD'].ewm(span=9, adjust=False).mean()
    x['MACD_HIST'] = x['MACD'] - x['MACD_SIGNAL']
    previous = close.shift(1)
    tr = pd.concat([(x['High']-x['Low']), (x['High']-previous).abs(), (x['Low']-previous).abs()], axis=1).max(axis=1)
    x['ATR14'] = tr.ewm(alpha=1/14, adjust=False).mean()
    x['VOL20'] = x['Volume'].rolling(20).mean()
    x['SUPPORT20'] = x['Low'].shift(1).rolling(20).min()
    x['RESIST20'] = x['High'].shift(1).rolling(20).max()
    return x

def classify(row):
    if row['EMA20'] > row['EMA60'] and row['Close'] > row['EMA20'] and row['MACD_HIST'] > 0:
        return '上涨确认'
    if row['EMA20'] < row['EMA60'] and row['Close'] < row['EMA20'] and row['MACD_HIST'] < 0:
        return '下跌确认'
    if row['EMA20'] > row['EMA60'] and row['Close'] < row['EMA20']:
        return '上涨减弱'
    if row['EMA20'] < row['EMA60'] and row['Close'] > row['EMA20']:
        return '下跌反弹'
    return '震荡/待确认'

def analyze(df, settings: Settings):
    x = indicators(df)
    if len(x) < 90:
        raise ValueError('至少需要90根日K线才能进行分析。')
    x['STATE'] = x.apply(classify, axis=1)
    last, prev = x.iloc[-1], x.iloc[-2]
    price, atr = float(last['Close']), float(last['ATR14'])
    support, resistance = float(last['SUPPORT20']), float(last['RESIST20'])
    bullish = last['STATE'] == '上涨确认'
    stop = min(support, price - settings.atr_multiple * atr)
    risk_share = max(price-stop, 0)
    target = price + settings.min_rr*risk_share
    shares_risk = int((settings.account * settings.risk_pct / 100) // risk_share) if risk_share > 0 else 0
    shares_cash = int(settings.account // price) if price > 0 else 0
    shares = max(0, min(shares_risk, shares_cash))
    trend_changed = str(last['STATE']) != str(prev['STATE'])
    signal = '观察候选（非买入指令）' if bullish and last['RSI14'] < 75 else '等待，不追单'
    if bullish and last['RSI14'] >= 75:
        signal = '趋势偏强但短期过热，等待'
    return x, {
        'date': str(x.index[-1].date()), 'price': price, 'state': last['STATE'], 'previous_state': prev['STATE'],
        'changed': trend_changed, 'signal': signal, 'rsi': float(last['RSI14']),
        'macd_hist': float(last['MACD_HIST']), 'atr': atr, 'support': support, 'resistance': resistance,
        'ema20': float(last['EMA20']), 'ema60': float(last['EMA60']),
        'volume_ratio': float(last['Volume']/last['VOL20']) if last['VOL20'] else float('nan'),
        'entry_reference': price, 'stop': stop, 'target': target, 'risk_per_share': risk_share,
        'shares': shares, 'cash_limited_shares': shares_cash, 'risk_limited_shares': shares_risk,
        'planned_max_loss': shares*risk_share,
    }

def swing_history(x):
    """Ex-post state transitions; not an executed trading backtest."""
    states = x['STATE'].tolist()
    records = []
    active = None
    for i, state in enumerate(states):
        if state == '上涨确认' and active is None:
            active = i
        elif state != '上涨确认' and active is not None:
            a, b = active, i
            p0, p1 = float(x['Close'].iloc[a]), float(x['Close'].iloc[b])
            segment = x.iloc[a:b+1]
            records.append({'开始': str(x.index[a].date()), '结束': str(x.index[b].date()),
                            '持续交易日': b-a, '起点价格': round(p0, 2), '终点价格': round(p1, 2),
                            '区间涨跌幅%': round((p1/p0-1)*100, 2),
                            '期间最大回撤%': round((segment['Close']/segment['Close'].cummax()-1).min()*100, 2),
                            '结束原因': state})
            active = None
    return pd.DataFrame(records[::-1])
