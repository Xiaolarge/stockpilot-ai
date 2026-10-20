import datetime as dt
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from plotly.subplots import make_subplots
from engine import Settings, analyze, swing_history

st.set_page_config(page_title='StockPilot AI', page_icon='📈', layout='wide')
st.title('📈 StockPilot AI｜美股波段分析')
st.caption('第一阶段 · 日线规则引擎 · 美元计价 · 不执行自动交易')

@st.cache_data(ttl=900, show_spinner=False)
def fetch(ticker, period):
    frame = yf.Ticker(ticker).history(period=period, interval='1d', auto_adjust=True)
    if frame.empty:
        raise ValueError('数据为空，请核对代码、网络或行情服务状态。')
    if frame.index.tz is not None:
        frame.index = frame.index.tz_convert('America/New_York').tz_localize(None)
    return frame

with st.sidebar:
    st.header('分析设置')
    ticker = st.text_input('美股代码', value='NVDA').strip().upper()
    period = st.selectbox('历史数据范围', ['1y','2y','5y'], index=1)
    account = st.number_input('可用资金 USD', min_value=1.0, value=650.0, step=50.0)
    risk_pct = st.slider('单笔计划风险占资金 %', 0.25, 3.0, 1.0, 0.25)
    atr_mult = st.slider('ATR 止损倍数', 1.0, 4.0, 2.0, 0.25)
    rr = st.slider('最低目标风险收益比', 1.0, 4.0, 2.0, 0.25)
    st.caption('行情来源：Yahoo Finance / yfinance；可能延迟、缺失或受限。价格经过拆股及分红调整，仅供研究。')
    st.caption('使用日线收盘数据，推荐观察3–15个交易日；不是盘中实时买卖信号。')

if not ticker or not ticker.replace('-', '').replace('.', '').isalnum():
    st.error('请输入有效股票代码。')
    st.stop()
try:
    raw = fetch(ticker, period)
    data, result = analyze(raw, Settings(account, risk_pct, atr_mult, rr))
except Exception as exc:
    st.error(f'无法完成分析：{exc}')
    st.info('请检查网络，稍后重试；也可以更换股票代码。')
    st.stop()

st.info(f"**{ticker}** · 最近日线：{result['date']}（美国东部交易日） · 页面刷新：{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · 数据可能延迟")
cols = st.columns(5)
for col, label, value in zip(cols,
    ['参考收盘价','波段状态','观察结论','RSI14','成交量/20日均量'],
    [f"${result['price']:.2f}", result['state'], result['signal'], f"{result['rsi']:.1f}", f"{result['volume_ratio']:.2f}×"]):
    col.metric(label, value)
if result['changed']:
    st.warning(f"波段状态刚发生变化：{result['previous_state']} → {result['state']}（以最新日K线为准）")

st.subheader('价格走势与技术指标')
chart = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=.035,
                      row_heights=[.60,.20,.20], subplot_titles=('K线 / EMA / 支撑阻力','成交量','MACD'))
chart.add_trace(go.Candlestick(x=data.index, open=data.Open, high=data.High, low=data.Low, close=data.Close, name='日K'), row=1,col=1)
for col, name, color in [('EMA20','EMA20','#ffbb55'),('EMA60','EMA60','#58b4f5'),('SUPPORT20','前20日支撑','#38b87c'),('RESIST20','前20日压力','#ee7777')]:
    chart.add_trace(go.Scatter(x=data.index,y=data[col],name=name,line=dict(color=color,width=1.5)),row=1,col=1)
chart.add_trace(go.Bar(x=data.index,y=data.Volume,name='成交量',marker_color='#7997b0'),row=2,col=1)
chart.add_trace(go.Bar(x=data.index,y=data.MACD_HIST,name='MACD柱',marker_color='#b89cff'),row=3,col=1)
chart.add_trace(go.Scatter(x=data.index,y=data.MACD,name='MACD',line=dict(color='#f3bd60')),row=3,col=1)
chart.add_trace(go.Scatter(x=data.index,y=data.MACD_SIGNAL,name='信号线',line=dict(color='#62c1d6')),row=3,col=1)
chart.update_layout(height=750,xaxis_rangeslider_visible=False,template='plotly_dark',legend=dict(orientation='h',y=-.09))
st.plotly_chart(chart,use_container_width=True)

st.subheader('参考交易计划（仅在上涨确认后评估）')
if result['state'] != '上涨确认':
    st.warning('当前未满足上涨确认规则，以下价格仅供观察，不建议直接据此下单。')
if result['shares'] == 0:
    st.warning('按当前资金、整股交易和风险上限，建议股数为0。可等待机会或调整资金规划；不要为了凑一股而突破风险预算。')
a,b,c,d = st.columns(4)
a.metric('观察入场参考', f"${result['entry_reference']:.2f}")
b.metric('模型止损参考', f"${result['stop']:.2f}")
c.metric('2R+ 目标参考', f"${result['target']:.2f}")
d.metric('风险约束下整股数', str(result['shares']))
st.caption(f"前20日支撑 ${result['support']:.2f} · 前20日压力 ${result['resistance']:.2f} · ATR14 ${result['atr']:.2f} · 单股计划风险 ${result['risk_per_share']:.2f} · 总计划亏损 ${result['planned_max_loss']:.2f} USD")
st.caption('目标价为数学上的风险收益比参考，不是预测。跳空、滑点和费用可能令实际亏损高于计划值。')

st.subheader('历史波段记录')
history = swing_history(data)
if history.empty:
    st.info('所选历史范围内尚无已结束的上涨确认区间。')
else:
    st.dataframe(history, use_container_width=True, hide_index=True)
    st.download_button('下载波段记录 CSV',history.to_csv(index=False).encode('utf-8-sig'),file_name=f'{ticker}_swings.csv',mime='text/csv')
    st.caption('历史波段按状态切换记录，非实际成交、非可交易回测；不等于策略收益或胜率。')

with st.expander('规则说明与局限', expanded=False):
    st.markdown('''- **上涨确认**：EMA20 > EMA60，收盘价 > EMA20，MACD柱 > 0。\n- **下跌确认**：EMA20 < EMA60，收盘价 < EMA20，MACD柱 < 0。\n- **上涨减弱**：EMA20 > EMA60，但收盘价跌破EMA20。\n- **下跌反弹**：EMA20 < EMA60，但收盘价突破EMA20。\n- **止损**：取前20日低点与「收盘价－2×ATR」中较低者（参数可调）。\n- **仓位**：不超过账户可买整股数，且计划亏损不超过风险预算。\n- **历史记录**：按收盘后已知信号标注区间；不包含交易费用、滑点或可执行回测。\n- **尚未实现**：自动扫描纳指100、财报解读、新闻分析、后台提醒、账户连接及自动交易。后续阶段添加。''')
st.caption('免责声明：软件提供规则化研究辅助，不构成个性化投资建议。市场可能发生跳空及重大损失。')
