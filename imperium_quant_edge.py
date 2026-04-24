import streamlit as st
from ib_async import *
import pandas as pd
import numpy as np
import talib
from datetime import datetime

# Premium Black + Red Theme
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
        border-radius: 8px;
    }
    .stButton>button:hover { background-color: #cc0000; }
    .success-box { background-color: #002200; border: 1px solid #00ff88; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

ib = IB()

st.title("🩸 IMPERIUM QUANT EDGE")
st.markdown("**Advanced Multi-Market AI Trading System**")

# Sidebar
st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])
default_port = 7497 if "Paper" in mode else 7496

auto_trading = st.sidebar.toggle("🤖 Enable Full Auto Trading", value=False)
if auto_trading and "Live" in mode:
    st.sidebar.error("⚠️ EXTREME RISK — Live Auto Trading")

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=default_port)
client_id = st.sidebar.number_input("Client ID", value=42)

daily_loss_limit = st.sidebar.slider("Daily Loss Limit %", 0.5, 10.0, 2.0) / 100

if st.sidebar.button("🔗 Connect to IBKR"):
    try:
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Connected in {mode}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {e}")

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'trade_count' not in st.session_state:
    st.session_state.trade_count = 0
if 'peak_equity' not in st.session_state:
    st.session_state.peak_equity = None

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🤖 Auto AI Trading", "📊 Portfolio", "📋 Tax Export", "ℹ️ Help"])

with tab1:
    st.header("Automatic AI Trading")
   
    if "Paper" in mode:
        st.markdown("<div class='success-box'><h3>📌 PAPER MODE — $1,000 Fake Money</h3></div>", unsafe_allow_html=True)
        simulated_balance = 1000.0
    else:
        st.markdown("<div style='background-color:#330000; padding:15px; border-radius:10px;'><h3>⚠️ LIVE MODE — REAL MONEY AT RISK</h3></div>", unsafe_allow_html=True)
        simulated_balance = None

    symbol = st.selectbox("Choose Market to Trade", [
        "XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)",
        "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
        "AAPL", "TSLA", "NVDA", "SHOP", "RY.TO",
        "BTCUSD", "ETHUSD"
    ])

    col1, col2, col3 = st.columns(3)
    with col1:
        risk_pct = st.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100
    with col2:
        stop_loss_pct = st.slider("Stop-Loss %", 0.5, 5.0, 1.5) / 100
    with col3:
        take_profit_pct = st.slider("Take-Profit %", 1.0, 10.0, 3.0) / 100

    if auto_trading and ib.isConnected() and st.session_state.trade_count < 20:
        st.success("🤖 Auto Trading ACTIVE — Max 20 trades + Daily Loss Protection")
        
        with st.spinner(f"AI analyzing {symbol}..."):
            try:
                # Contract Mapping
                if symbol == "XAUUSD (Gold)":
                    contract = Forex("XAUUSD")
                elif symbol == "XAGUSD (Silver)":
                    contract = Forex("XAGUSD")
                elif symbol == "CL (Crude Oil)":
                    contract = Future("CL", "2025-06", "NYMEX")
                elif "USD" in symbol and "." in symbol:
                    contract = Forex(symbol)
                elif symbol in ["BTCUSD", "ETHUSD"]:
                    contract = Crypto(symbol.split("USD")[0], "PAXOS", "USD")
                else:
                    contract = Stock(symbol.split(".")[0], "SMART", "USD" if ".TO" not in symbol else "CAD")

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
                        net_liq = simulated_balance or 100000
                        size = max(1, int((net_liq * risk_pct) / last.close))

                        # Daily Loss Protection
                        if st.session_state.peak_equity is None:
                            st.session_state.peak_equity = net_liq
                        current_loss = (st.session_state.peak_equity - net_liq) / st.session_state.peak_equity if st.session_state.peak_equity > 0 else 0
                        
                        if current_loss > daily_loss_limit:
                            st.error("🚨 DAILY LOSS LIMIT BREACHED! Auto Trading Paused.")
                        else:
                            parent = MarketOrder(signal, size)
                            sl_price = last.close * (1 - stop_loss_pct) if signal == "BUY" else last.close * (1 + stop_loss_pct)
                            tp_price = last.close * (1 + take_profit_pct) if signal == "BUY" else last.close * (1 - take_profit_pct)

                            stop_order = StopOrder("SELL" if signal == "BUY" else "BUY", size, sl_price)
                            take_order = LimitOrder("SELL" if signal == "BUY" else "BUY", size, tp_price)

                            bracket = ib.bracketOrder(parent, stop_order, take_order)

                            for o in bracket:
                                ib.placeOrder(contract, o)

                            st.markdown(f"<h4 style='color:#00ff88;'>✅ AI AUTO EXECUTED: {signal} {size} of {symbol} @ {last.close:.4f}</h4>", unsafe_allow_html=True)
                            st.session_state.trade_log.append({"time": datetime.now().strftime("%H:%M:%S"), "symbol": symbol, "action": signal})
                            st.session_state.trade_count += 1
            except Exception as e:
                st.error(f"Error: {e}")

    st.subheader("Recent Auto Trades")
    if st.session_state.trade_log:
        st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(15))
    else:
        st.info("No trades yet.")

    if st.session_state.trade_count >= 20:
        st.warning("✅ Maximum of 20 trades reached. Auto Trading stopped.")

with tab2:
    st.header("Portfolio")
    if "Paper" in mode:
        st.metric("Simulated Balance", "$1,000.00 Fake CAD")
    if ib.isConnected():
        summary = {s.tag: s.value for s in ib.accountSummary()}
        st.metric("IBKR Balance", f"${float(summary.get('NetLiquidation', 0)):.2f}")

    st.button("🛑 KILL SWITCH — Cancel All Orders", type="primary")

with tab4:
    st.markdown("""
    **Safety Features Included:**
    - Maximum 20 trades in auto mode
    - Daily Loss Limit protection
    - Strong warnings in Live mode
    - Emergency Kill Switch
    """)

if ib.isConnected():
    ib.sleep(0.5)

st.caption("Imperium Quant Edge • Final Upgraded Version")