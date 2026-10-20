# StockPilot AI — 第一阶段

中文美股日线波段观察工具。支持任意 Yahoo Finance 可识别的美股代码（例如 NVDA、GOOGL、AMZN、AMD、QQQM）。

## 安装与运行

需要 Python 3.10 或更新版本、可访问 Yahoo Finance 的网络。

### Windows PowerShell

```powershell
cd stockpilot_ai
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

浏览器打开终端提示的地址（通常是 http://localhost:8501）。关闭终端会停止程序。

如果 PowerShell 禁止激活虚拟环境，可不激活，直接运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
cd stockpilot_ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 使用

1. 左侧输入股票代码（例如 NVDA）。
2. 选择历史数据范围、美元资金、每笔风险比例。
3. 阅读「波段状态」「观察结论」，再查看图表、支撑压力和计划价格。
4. 如需保存历史波段，点击 CSV 下载。

## 数据与局限

- 使用 yfinance 获取 Yahoo Finance 日线数据，可能延迟、受限或不可用，不保证实时性与完整性。
- 收盘价采用 auto_adjust=True 的调整后价格，适合技术研究，但可能与券商显示的历史原始成交价不同。
- 波段状态基于 EMA20、EMA60、MACD，属于简单、可解释的启发式规则，并非保证有效的交易策略。
- 历史波段仅是事后区间统计，不是成交回测，不包含费用、滑点、税金与股息。
- 止损是风险预算参考，跳空可能导致实际亏损超出预算。
- 第一阶段**不含**财报自动解读、纳指100自动筛选、通知或自动交易；后续阶段开发。
- 仅供研究和教育用途，不构成投资建议。

## 文件结构

- `app.py`：Streamlit 界面、行情获取、K线与下载
- `engine.py`：指标、波段分类、风险计算、历史区间
- `requirements.txt`：依赖
- `test_engine.py`：无网络测试

## 第二阶段新增功能（v2）

继续使用同一套依赖，在 `stockpilot_ai` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app_phase2.py
```

第二阶段入口 `app_phase2.py`：四个选项卡分别提供纳指候选池自动扫描、财报字段与季度利润表、历史交易回测和多股对比。第一阶段 `app.py` 仍然可以独立运行。

- 扫描支持内置30只候选池，或尝试从 Wikipedia 获取**当前**纳斯达克100成分股。在线名单失败时回退内置池；批量请求 Yahoo Finance 可能受到限流。评分仅含技术和流动性因素，**不包含财报评分**。
- 财报使用 yfinance 提供的公司资料和季度利润表；不保证完整、及时、统一口径。EPS预期差和业绩指引尚未可靠接入，不应凭空推断。
- 回测使用当日收盘信号、**下一交易日开盘**入场；趋势失效和超期在下一开盘退出，止损按跳空开盘价或止损价执行，模拟滑点和固定手续费。最多持有15日（可调）。仓位受可用现金和每笔风险预算约束。未平仓仅按最后收盘价计入权益，不算已平仓胜率。
- 回测使用拆股/分红调整后的 OHLC 作为研究代理，非真实历史逐笔成交；不含税金、流动性冲击、融资利息，不能保证策略收益。名单为当前成分股，存在幸存者偏差，不可作为历史纳指100策略的严谨回测。
- 依赖网络才能使用行情和财报功能。没有 API key 的情况下无法保证实时或稳定更新。

新增文件：`phase2.py`（策略、评分和财务整理），`app_phase2.py`（第二阶段页面），`test_phase2.py`（离线测试）。

## v3: 美日股超跌反弹雷达
运行 `streamlit run app_phase3.py`。选择美股、日股或全部，输入分别计价的资金、单笔风险、持有交易日及日股交易单位。扫描后可查看每只股票的超跌状态、观察入场区间、参考止损、止盈、风险预算和股数，并导出 CSV。

**重要：** 条件区间基于最新可获取日线收盘数据，不是实时报价；市场价格和公司财报可能改变判断。日股通常为100股一手，券商单股服务可能存在限制。反弹评分未经样本外验证，属于研究工具，不提供自动下单或后台提醒。

## v4: 手续费自动计算 + 手机网页使用

运行 `streamlit run app_phase3.py`。美股默认**买入固定0.38美元，卖出固定0.38美元**（每笔交易订单固定收费的假设；请核实券商实际费用）。日股默认0日元，需按日股券商实际收费填写。自动计算保本卖价、目标净利润、扣费后风险收益比，且仓位计算同时约束手续费与风险预算。仅当参考股数大于0时才有可执行的保本价。该模块不含税费、滑点、汇兑费和券商其他收费。

### 手机访问（重要）

**下载ZIP到手机并不能直接打开运行 Streamlit**。必须先在一台电脑或云端服务器启动 Python 服务。两种方法：

1. **同一Wi-Fi局域网访问**：电脑执行 `python -m streamlit run app_phase3.py --server.address 0.0.0.0`，查找电脑的局域网 IPv4 地址，手机 Safari 访问 `http://电脑IP:8501`。Windows 防火墙需要允许私有网络入站 8501 端口；不要直接把此端口暴露到公网。电脑关机则手机无法访问。
2. **手机随时访问（推荐）**：将项目上传到自己的**私有或公开 GitHub 仓库**，在 https://share.streamlit.io/ 使用 Streamlit Community Cloud 创建 App，选择仓库、分支，并将 Main file path 设为 `app_phase3.py`。部署成功后平台会给出 `https://...streamlit.app` 的专属网址，手机 Safari 直接打开。注意免费服务可能休眠、存在资源限制，且公网部署应注意访问控制。此项目未由助手代为部署，尚无可打开的在线网址。

数据从 Yahoo Finance 读取，可能延迟或限流。手机页面支持 Streamlit 自适应布局，但部分宽表需左右滑动。
