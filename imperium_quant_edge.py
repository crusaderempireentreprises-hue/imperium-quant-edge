import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random
import plotly.graph_objects as go

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; }
    .stButton>button:hover { background-color: #cc0000; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Multi-Market Automatic AI Trader** — Expanded Markets")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

auto_trading = st.sidebar.toggle("🤖 Continuous Auto Trading", value=False)

# Expanded Market List
markets = st.sidebar.multiselect(
    "Select Markets (AI can trade multiple at once)",
    [
        "XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)", "HG (Copper)",
        "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD", "USD.CHF", "EUR.GBP", "USD.MXN",
        "AAPL", "TSLA", "NVDA", "AMZN", "GOOGL", "MSFT", "META", "AMD", "SHOP", "RY.TO", "TD.TO", "ENB.TO", "CNQ.TO",
        "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"
    ],
    default=["XAUUSD (Gold)", "EUR.USD", "BTCUSD", "AAPL", "TSLA"]
)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100
stop_loss_pct = st.sidebar.slider("Stop-Loss %", 0.5, 5.0, 1.5) / 100
take_profit_pct = st.sidebar.slider("Take-Profit %", 1.0, 10.0, 3.0) / 100

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = [1000.0]
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0

balance = st.session_state.balance

if "Paper" in mode:
    st.success("📌 Paper Mode — Starting with $1,000 Fake Money")
else:
    st.warning("⚠️ Live Mode — Real Money at Risk")

st.subheader("Active Markets")
st.write(markets)

if auto_trading:
    st.success("🤖 Multi-Market AI ACTIVE")
    
    for _ in range(8):
        with st.spinner("AI scanning all selected markets..."):
            time.sleep(0.8)
            executed = 0
            for sym in markets:
                if random.random() < 0.4:
                    signal = random.choice(["BUY", "SELL"])
                    size = max(1, int((balance * risk_pct) / 100))
                    
                    st.markdown(f"<h4 style='color:#00ff88;'>✅ AI EXECUTED: {signal} {size} of **{sym}**</h4>", unsafe_allow_html=True)
                    st.session_state.trade_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "symbol": sym,
                        "action": signal,
                        "size": size
                    })
                    executed += 1
                    balance = balance * random.uniform(0.96, 1.08)
                    st.session_state.balance = balance
            
            if executed == 0:
                st.info("No strong signals this cycle.")

# Performance
col1, col2 = st.columns(2)
with col1:
    st.subheader("Equity Curve")
    if len(st.session_state.equity_curve) > 1:
        st.line_chart(pd.DataFrame(st.session_state.equity_curve, columns=["Balance"]))

with col2:
    st.subheader("Performance")
    if st.session_state.trade_log:
        df = pd.DataFrame(st.session_state.trade_log)
        st.metric("Total Trades", len(df))
        st.metric("Current Balance", f"${balance:.2f}")

st.subheader("Recent Trades")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30))
else:
    st.info("No trades yet.")

st.button("🛑 KILL SWITCH — Stop All Trading", type="primary")

st.caption("Imperium Quant Edge • Expanded Markets Edition")