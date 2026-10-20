"""StockPilot AI Phase 3: US/JP rebound radar and conditional trading plans."""
import datetime as dt
import pandas as pd
import streamlit as st
import yfinance as yf
from rebound import US,JP,rebound_plan
from fees import net_result
st.set_page_config(page_title='StockPilot AI v3 超跌反弹雷达',page_icon='📡',layout='wide')
st.title('📡 StockPilot AI｜美日股超跌反弹雷达')
st.caption('寻找近期急跌、出现反弹确认的股票；价格为条件参考，不是保证成交价或投资指令。')
@st.cache_data(ttl=1800,show_spinner=False)
def history(symbol):
    data=yf.Ticker(symbol).history(period='1y',interval='1d',auto_adjust=True)
    if data.empty: raise ValueError('行情为空')
    return data
with st.sidebar:
    st.header('交易设置')
    market=st.radio('市场',['美股 USD','日股 JPY','全部'])
    us_cash=st.number_input('美股资金 USD',min_value=0.,value=650.,step=50.)
    jp_cash=st.number_input('日股资金 JPY',min_value=0.,value=100000.,step=10000.)
    risk=st.slider('单笔计划最大风险占本金 %',.25,3.,1.,.25)
    hold=st.slider('最多持有交易日',3,20,10)
    jp_lot=st.selectbox('日股买卖单位',[100,1],index=0,help='普通日股通常100股一手；1股仅适用于支持单元未满股交易的券商。')
    st.subheader('交易手续费（每笔固定）')
    us_fee=st.number_input('美股单次手续费 USD',min_value=0.,value=.38,step=.01,format='%.2f')
    jp_fee=st.number_input('日股单次手续费 JPY',min_value=0.,value=0.,step=1.,help='请填入券商日股真实日元费用，不能把美元0.38直接当日元。')
    st.caption('买入、卖出各收一次；默认美股往返0.76美元。其他平台费、汇兑、税费、滑点尚未包含。')
    st.caption('日股、美股资金分开计算，不自动兑换汇率。')
st.info('信号逻辑：过去12个交易日出现20日高点回撤≥10%，近12日RSI曾低于35，随后价格收复EMA20、RSI上升且量比≥1.2。未满足全部条件时只观察。')
if st.button('扫描美股与日股候选',type='primary'):
    tickers=(US if market=='美股 USD' else JP if market=='日股 JPY' else US+JP)
    rows=[]; errors=[]
    prog=st.progress(0)
    for i,s in enumerate(tickers):
        try:
            rows.append(rebound_plan(s,history(s),us_cash if s in US else jp_cash,risk,1 if s in US else jp_lot,hold,buy_fee=us_fee if s in US else jp_fee,sell_fee=us_fee if s in US else jp_fee))
        except Exception as e: errors.append(f'{s}: {str(e)[:110]}')
        prog.progress((i+1)/len(tickers))
    st.session_state['rebound_rows']=rows
    st.session_state['rebound_errors']=errors
    st.session_state['rebound_time']=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
if st.session_state.get('rebound_rows'):
    rows=pd.DataFrame(st.session_state['rebound_rows'])
    rows=rows.sort_values(['反弹评分','量比'],ascending=False)
    st.caption('扫描时间：'+st.session_state['rebound_time']+'；逐只查看数据日期；行情可能延迟。')
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.download_button('导出反弹候选与交易计划 CSV',rows.to_csv(index=False).encode('utf-8-sig'),'rebound_plans.csv','text/csv')
    selected=st.selectbox('查看单股计划',rows['代码'].tolist())
    item=rows.loc[rows['代码']==selected].iloc[0]
    st.subheader(selected+' · '+item['状态'])
    a,b,c,d=st.columns(4)
    a.metric('观察买入区间',f"{item['观察入场下沿']:,.2f}–{item['观察入场上沿']:,.2f} {item['币种']}")
    b.metric('参考止损',f"{item['参考止损']:,.2f} {item['币种']}")
    c.metric('参考止盈',f"{item['参考止盈']:,.2f} {item['币种']}")
    d.metric('最长观察持有',f"{item['计划持有交易日']}交易日")
    st.write(f"参考股数：**{item['参考股数']}**；价格风险（不含手续费）：**{item['计划风险金额']:,.2f} {item['币种']}**；毛风险收益比：**{item['风险收益比']}**。")
    st.write(f"买卖往返手续费：**{item['往返手续费']:.2f} {item['币种']}**；保本卖出价：**{item['保本卖价'] if pd.notna(item['保本卖价']) else '无可执行仓位'}**；达到参考止盈时的净利润：**{item['目标净利润'] if pd.notna(item['目标净利润']) else '无'}**；扣费后风险收益比：**{item['扣费后风险收益比']}**。")
    if item['参考股数']==0: st.warning('按照当前资金、整股/日股交易单位和风险限制，没有可执行仓位。')
    st.warning('只在反弹状态确认、价格进入区间且未出现重大利空时考虑交易；若开盘跳空超过区间上沿，放弃追价并重新计算。触及止损退出；达到止盈考虑退出；即使未触及价格条件，达到最长持有期也重新评估。隔夜跳空可能造成超出计划的损失。')
    st.line_chart(history(selected)['Close'])
if st.session_state.get('rebound_errors'):
    with st.expander('数据读取失败记录'):
        st.write(st.session_state['rebound_errors'])
st.divider()
st.caption('v2的财报、回测、多股比较仍可通过 streamlit run app_phase2.py 使用。本页的反弹评分未经独立样本外验证，不能解读为上涨概率。')

st.divider()
st.subheader('🧮 手机可用的手续费与净收益计算器')
c1,c2=st.columns(2)
with c1:
    calc_buy=st.number_input('实际买入单价',min_value=0.01,value=200.,step=1.,key='calc_buy')
    calc_qty=st.number_input('实际股数',min_value=1,value=2,step=1,key='calc_qty')
with c2:
    calc_sell=st.number_input('计划卖出单价',min_value=0.,value=210.,step=1.,key='calc_sell')
    calc_market=st.selectbox('计价市场',['美股 USD','日股 JPY'],key='calc_market')
calc_fee=us_fee if calc_market=='美股 USD' else jp_fee
result=net_result(calc_buy,calc_sell,calc_qty,calc_fee,calc_fee)
x,y,z=st.columns(3)
x.metric('净利润',f"{result['net']:.2f}")
y.metric('净收益率',f"{result['net_pct']:.2f}%")
z.metric('保本卖价',f"{result['break_even']:.4f}")
st.caption(f"毛利润 {result['gross']:.2f}，往返手续费 {result['fees']:.2f}。不含税、滑点和汇兑成本。")
