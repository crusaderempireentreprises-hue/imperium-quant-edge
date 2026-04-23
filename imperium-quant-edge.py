import streamlit as st
from ib_async import *
import pandas as pd
import numpy as np
import talib
from datetime import datetime

# Black + Red Theme
st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { 
        background-color: #990000; 
        color: white; 
        border: 2px solid #ff0000; 
        font-weight: bold; 
    }
    .stButton>button:hover { background-color: #cc0000; }
</style>
""", unsafe_allow_html=True)

ib = IB()

st.title("🩸 Imperium Quant Edge")
st.markdown("**Personal Automatic AI Trader** — Black & Red Edition")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])
default_port = 7497 if "Paper" in mode else 7496

auto_trading = st.sidebar.toggle("🤖 Enable Full Auto Trading (AI buys & sells automatically)", value=False)

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=default_port)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("Connect to IBKR"):
    try:
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Connected in {mode}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {e}")

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🤖 Auto AI Trading", "📊 Portfolio", "📋 Tax Export", "ℹ️ Help"])

with tab1:
    st.header("Automatic AI Trading")
    
    if "Paper" in mode:
        st.markdown("<h3 style='color:#ff3333;'>📌 Paper Mode — Starting with $1,000 Fake Money</h3>", unsafe_allow_html=True)
        simulated_balance = 1000.0
    else:
        st.warning("⚠️ LIVE MODE ACTIVE — Real money will be used. Proceed with extreme caution.")
        simulated_balance = None

    symbol = st.selectbox("Symbol to Trade", ["EUR.USD", "USD.CAD", "GBP.USD", "AAPL", "TSLA", "BTCUSD"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        risk_pct = st.slider("Risk % per Trade", 0.25, 5.0, 0.5) / 100   # lowered default for safety
    with col2:
        stop_loss_pct = st.slider("Stop-Loss %", 0.5, 5.0, 1.5) / 100
    with col3:
        take_profit_pct = st.slider("Take-Profit %", 1.0, 10.0, 3.0) / 100

    if auto_trading and ib.isConnected():
        st.success("🤖 Auto Trading is ACTIVE — AI will automatically buy and sell")
        
        with st.spinner(f"AI analyzing {symbol}..."):
            try:
                if '.' in symbol:
                    contract = Forex(symbol)
                elif symbol == "BTCUSD":
                    contract = Crypto("BTC", "PAXOS", "USD")
                else:
                    contract = Stock(symbol, "SMART", "USD")

                bars = ib.reqHistoricalData(contract, '', '2 D', '15 mins', 'MIDPOINT', True, 1)
                if len(bars) >= 60:
                    df = util.df(bars)
                    df['rsi'] = talib.RSI(df.close, 14)
                    df['sma_fast'] = talib.SMA(df.close, 12)
                    df['sma_slow'] = talib.SMA(df.close, 26)

                    last = df.iloc[-1]
                    prev = df.iloc[-2]

                    signal = None
                    if last.sma_fast > last.sma_slow and prev.sma_fast <= prev.sma_slow and last.rsi < 70:
                        signal = "BUY"
                    elif last.sma_fast < last.sma_slow and prev.sma_fast >= prev.sma_slow and last.rsi > 30:
                        signal = "SELL"

                    if signal:
                        net_liq = simulated_balance or float(next((s.value for s in ib.accountSummary() if s.tag == 'NetLiquidation'), 10000))
                        size = max(1, int((net_liq * risk_pct) / last.close))

                        parent = MarketOrder(signal, size)
                        sl_price = last.close * (1 - stop_loss_pct) if signal == "BUY" else last.close * (1 + stop_loss_pct)
                        tp_price = last.close * (1 + take_profit_pct) if signal == "BUY" else last.close * (1 - take_profit_pct)

                        stop_order = StopOrder("SELL" if signal == "BUY" else "BUY", size, sl_price)
                        take_order = LimitOrder("SELL" if signal == "BUY" else "BUY", size, tp_price)

                        bracket = ib.bracketOrder(parent, stop_order, take_order)

                        for o in bracket:
                            ib.placeOrder(contract, o)

                        st.markdown(f"<h4 style='color:#00ff88;'>✅ AI AUTO EXECUTED: {signal} {size} of {symbol} @ {last.close:.4f}</h4>", unsafe_allow_html=True)
                        st.session_state.trade_log.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "symbol": symbol,
                            "action": signal,
                            "size": size
                        })
            except Exception as e:
                st.error(f"Analysis error: {e}")

    st.subheader("Recent Auto Trades")
    if st.session_state.trade_log:
        log_df = pd.DataFrame(st.session_state.trade_log)
        st.dataframe(log_df.tail(10))
    else:
        st.info("No trades yet. Turn on Auto Trading to start.")

with tab2:
    st.header("Portfolio")
    if "Paper" in mode:
        st.metric("Simulated Paper Balance", "$1,000.00 Fake CAD")
        st.info("Actual IBKR paper account may show higher balance — we simulate $1,000 here.")
    
    if ib.isConnected():
        summary = {s.tag: s.value for s in ib.accountSummary()}
        st.metric("Real IBKR Net Liquidation", f"${float(summary.get('NetLiquidation', 0)):.2f}")

    st.button("🛑 KILL SWITCH — Cancel All Orders", key="kill", type="primary")

with tab3:
    st.header("Tax Export")
    if st.button("Export Recent Trades CSV"):
        if ib.isConnected():
            executions = ib.executions()
            if executions:
                df = util.df([{"Time": e.time, "Symbol": e.contract.symbol, "Side": e.side, "Qty": getattr(e, 'shares', getattr(e, 'amount', 0)), "Price": e.price} for e in executions])
                st.download_button("Download CSV", df.to_csv(index=False).encode(), "imperium_trades.csv", "text/csv")

with tab4:
    st.markdown("""
    ### How to Use
    - **Paper Mode**: Safe testing with $1,000 fake money.
    - **Live Mode**: Real money — use at your own risk.
    - Turn on **Auto Trading** to let the AI buy and sell automatically.
    - Always keep IB Gateway running on your computer.

    **TD Canada Trust withdrawals**: Manual via IBKR Client Portal (CAD EFT recommended).

    Trade responsibly.
    """)

if ib.isConnected():
    ib.sleep(0.5)

st.caption("Imperium Quant Edge — Black & Red Edition • Personal Use Only")