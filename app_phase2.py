"""StockPilot AI Phase 2 multi-page companion; run with streamlit run app_phase2.py."""
import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf
from phase2 import CORE, scan_one, backtest, summarize_financials

st.set_page_config(page_title='StockPilot AI 第二阶段',page_icon='📊',layout='wide')
st.title('📊 StockPilot AI｜第二阶段')
st.caption('批量筛选 · 财报概览 · 可执行规则回测 · 多股对比｜研究用途，不自动下单')

@st.cache_data(ttl=1800,show_spinner=False)
def get_history(symbol,period='2y'):
    x = yf.Ticker(symbol).history(period=period,interval='1d',auto_adjust=True)
    if x.empty:
        raise ValueError('行情数据为空')
    if x.index.tz is not None:
        x.index=x.index.tz_convert('America/New_York').tz_localize(None)
    return x

@st.cache_data(ttl=7200,show_spinner=False)
def get_financial(symbol):
    ticker=yf.Ticker(symbol)
    info=ticker.info or {}
    income=ticker.quarterly_income_stmt
    return info,income

@st.cache_data(ttl=86400,show_spinner=False)
def nasdaq100_universe():
    """Wikipedia constituents are current, NOT point-in-time historical membership."""
    url='https://en.wikipedia.org/wiki/Nasdaq-100'
    tables=pd.read_html(url,match='Ticker')
    for table in tables:
        names=[str(c).lower() for c in table.columns]
        key=next((table.columns[i] for i,c in enumerate(names) if 'ticker' in c),None)
        if key is not None and len(table)>=80:
            return list(dict.fromkeys(table[key].astype(str).str.replace('.','-',regex=False).str.strip().tolist()))
    raise ValueError('未找到成分股表')

with st.sidebar:
    st.header('通用设置')
    capital=st.number_input('本金 USD',min_value=1.0,value=650.0,step=50.0)
    risk=st.slider('每笔计划风险 %',.25,3.,1.,.25)
    fee=st.number_input('每次成交手续费 USD',min_value=0.,value=0.,step=.5)
    slip=st.slider('单边滑点（基点）',0,100,10,5)
    fractional=st.checkbox('允许碎股（仅回测假设）',False)
    st.caption('Yahoo Finance 非保证实时，筛选和财报请求可能耗时或失败。')
    st.caption('旧版单股界面：streamlit run app.py')

p1,p2,p3,p4=st.tabs(['🔎 纳指自动选股','📑 财报分析','🧪 历史回测','⚖️ 多股比较'])
with p1:
    st.subheader('自动筛选候选股')
    scope=st.radio('股票池',['精选30只（快速）','纳斯达克100当前成分股（较慢）'],horizontal=True)
    st.caption('评分仅来自技术面与流动性，尚未自动把财报纳入评分；成分股名单是当前版本，不适用于历史成分股回测。')
    if st.button('开始扫描',type='primary'):
        symbols=CORE
        if scope.startswith('纳斯达克100'):
            try:
                symbols=nasdaq100_universe()
            except Exception as exc:
                st.warning(f'当前成分股名单获取失败，改用内置候选池：{exc}')
        rows=[]; errors=[]
        bar=st.progress(0)
        for idx,s in enumerate(symbols):
            try:
                rows.append(scan_one(s,get_history(s,'1y')))
            except Exception as exc:
                errors.append(f'{s}: {str(exc)[:75]}')
            bar.progress((idx+1)/len(symbols))
        if rows:
            ranked=pd.DataFrame(rows).sort_values(['评分/100','成交量比'],ascending=False).reset_index(drop=True)
            st.session_state['ranked']=ranked
            st.session_state['scan_at']=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        st.session_state['scan_errors']=errors
    if 'ranked' in st.session_state:
        st.caption('扫描完成时间：'+st.session_state['scan_at']+'；不同股票最后交易日可能不同，请检查「数据日期」。')
        st.dataframe(st.session_state['ranked'],use_container_width=True,hide_index=True)
        st.download_button('下载选股排名 CSV',st.session_state['ranked'].to_csv(index=False).encode('utf-8-sig'),'stockpilot_ranking.csv','text/csv')
    if st.session_state.get('scan_errors'):
        with st.expander(f'查看 {len(st.session_state["scan_errors"])} 个数据获取失败项'):
            st.write(st.session_state['scan_errors'])
with p2:
    sym=st.text_input('财报分析股票代码','NVDA',key='finance_sym').strip().upper()
    if st.button('读取财务信息'):
        try:
            info,income=get_financial(sym)
            st.caption(f'读取时间 {dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}；字段更新周期不一，非财报披露时间。')
            st.dataframe(summarize_financials(info,income),use_container_width=True,hide_index=True)
            if income is not None and not income.empty:
                st.subheader('季度利润表（来源原始字段）')
                st.dataframe(income.iloc[:25,:4],use_container_width=True)
                st.download_button('下载季度利润表 CSV',income.to_csv().encode('utf-8-sig'),f'{sym}_income.csv','text/csv')
            else:
                st.warning('暂无可用季度利润表。')
            st.info('财报分析说明：正增长不等于超预期。EPS实际值与分析师一致预期、业绩指引及电话会议内容尚未建立可靠结构化数据源，因此本版不计算财报超预期评分。')
            st.markdown(f'[打开 {sym} 的 SEC 官方申报查询](https://www.sec.gov/edgar/search/)')
        except Exception as exc:
            st.error(f'财报数据暂不可用：{exc}')
with p3:
    symbol=st.text_input('回测代码','NVDA',key='bt_sym').strip().upper()
    period=st.selectbox('回测历史范围',['1y','2y','5y'],index=1)
    maxbars=st.slider('最多持仓交易日',3,30,15)
    if st.button('运行回测',type='primary'):
        try:
            df=get_history(symbol,period)
            deals,curve,stats=backtest(df,capital,risk,fee,slip,2,maxbars,fractional)
            st.session_state['bt']=(symbol,deals,curve,stats)
        except Exception as exc:
            st.error(f'回测失败：{exc}')
    if 'bt' in st.session_state:
        name,deals,curve,stats=st.session_state['bt']
        st.caption(f'{name} · 依据历史日线；已平仓交易才计入胜率；未平仓按最后收盘价估值。')
        cols=st.columns(5)
        for col,(k,v) in zip(cols,stats.items()):
            col.metric(k,'—' if v is None else str(v))
        st.plotly_chart(px.line(curve,x='日期',y='权益$',title='回测权益曲线（USD）'),use_container_width=True)
        if deals.empty:
            st.info('当前风险预算、整股约束和信号条件下，没有已完成交易。')
        else:
            st.dataframe(deals,use_container_width=True,hide_index=True)
            st.download_button('下载回测交易 CSV',deals.to_csv(index=False).encode('utf-8-sig'),f'{name}_backtest.csv','text/csv')
        st.warning('局限：调整后OHLC仅为研究代理；同日入场后止损采用保守规则，未模拟点差变化、税费、退市股票、公司行动及分时成交顺序。过往表现不保证未来结果。')
with p4:
    symbols=st.text_input('比较代码（逗号分隔，最多8只）','NVDA,GOOGL,AMZN,AMD').upper().replace(' ','').split(',')
    symbols=list(dict.fromkeys([s for s in symbols if s]))[:8]
    if st.button('比较股票'):
        rows=[]; series=[]; errors=[]
        for s in symbols:
            try:
                frame=get_history(s,'1y')
                rows.append(scan_one(s,frame))
                daily=frame['Close'].dropna()
                series.append((daily/daily.iloc[0]*100).rename(s))
            except Exception as exc:
                errors.append(f'{s}: {exc}')
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values('评分/100',ascending=False),use_container_width=True,hide_index=True)
            normalized=pd.concat(series,axis=1).ffill()
            st.plotly_chart(px.line(normalized,title='过去一年价格相对走势（首个数据点=100，调整后价格）'),use_container_width=True)
        if errors:
            st.warning('部分股票获取失败：'+'；'.join(errors))
st.divider()
st.caption('本程序不连接券商、不执行自动交易。所有建议为研究辅助；财报与排名数据需核实来源和日期。')
