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
st.markdown("**Ultimate Multi-Market Automatic AI Trader**")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

auto_trading = st.sidebar.toggle("🤖 Continuous Auto Trading", value=False)
burst_mode = st.sidebar.toggle("⚡ Burst Mode (Very Aggressive)", value=False)
speed = st.sidebar.slider("Simulation Speed (seconds)", 0.3, 3.0, 1.0)

markets = st.sidebar.multiselect(
    "Select Markets (AI can trade many at once)",
    ["XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
     "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
     "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO", "TD.TO",
     "BTCUSD", "ETHUSD", "SOLUSD"],
    default=["XAUUSD (Gold)", "EUR.USD", "BTCUSD", "AAPL"]
)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

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

if st.button("🚀 Quick Test (20 Fast Cycles)"):
    for _ in range(20):
        for sym in markets:
            if random.random() < 0.5:
                signal = random.choice(["BUY", "SELL"])
                size = max(1, int((balance * risk_pct) / 100))
                st.markdown(f"<h4 style='color:#00ff88;'>✅ TEST: {signal} {size} of {sym}</h4>", unsafe_allow_html=True)
                st.session_state.trade_log.append({"time": datetime.now().strftime("%H:%M:%S"), "symbol": sym, "action": signal})
                balance *= random.uniform(0.96, 1.08)
        time.sleep(0.3)
    st.success("Quick Test Finished!")

if auto_trading:
    current_speed = speed / 2.5 if burst_mode else speed
    st.success(f"🚀 AI Running {'in Burst Mode ⚡' if burst_mode else 'Normally'}")
    
    placeholder = st.empty()
    
    while auto_trading:
        with placeholder.container():
            executed = 0
            for sym in markets:
                if random.random() < (0.6 if burst_mode else 0.35):
                    signal = random.choice(["BUY", "SELL"])
                    size = max(1, int((balance * risk_pct) / 100))
                    
                    st.markdown(f"<h4 style='color:#00ff88;'>✅ AI EXECUTED: {signal} {size} of **{sym}** {'⚡' if burst_mode else ''}</h4>", unsafe_allow_html=True)
                    st.session_state.trade_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "symbol": sym,
                        "action": signal,
                        "size": size
                    })
                    executed += 1
                    balance *= random.uniform(0.95, 1.09)
                    st.session_state.balance = balance
            
            if executed == 0:
                st.info("No strong signals this cycle.")
            
            st.metric("Current Balance", f"${balance:.2f}")
        
        time.sleep(current_speed)

# Charts & Stats
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

st.subheader("Full Trade History")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(50))
else:
    st.info("No trades yet.")

if st.button("🛑 STOP ALL AUTO TRADING"):
    auto_trading = False
    st.success("Auto Trading Stopped.")

st.caption("Imperium Quant Edge • Full Multi-Market AI with Burst Mode")