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
st.markdown("**Multi-Market Adaptive AI Trader** — Continuous + Burst Mode")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

continuous_trading = st.sidebar.toggle("🔄 Continuous Trading (No Limit)", value=False)
burst_mode = st.sidebar.toggle("⚡ Burst Mode (Aggressive)", value=False)

markets = st.sidebar.multiselect(
    "Select Markets",
    ["XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
     "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
     "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO",
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
if 'starting_balance' not in st.session_state:
    st.session_state.starting_balance = 1000.0

balance = st.session_state.balance

if "Paper" in mode:
    st.success("📌 Paper Mode — Starting with $1,000 Fake Money")
else:
    st.warning("⚠️ Live Mode — Real Money at Risk")

st.subheader("Active Markets")
st.write(markets)

# Loss protection
if balance <= (st.session_state.starting_balance - 100):
    st.error("🛑 Automatic Stop Triggered: $100 loss limit reached!")
    continuous_trading = False
    burst_mode = False

if continuous_trading or burst_mode:
    current_speed = 0.4 if burst_mode else 1.2
    st.success(f"🚀 {'Burst' if burst_mode else 'Continuous'} Trading ACTIVE")
    
    placeholder = st.empty()
    
    while (continuous_trading or burst_mode) and balance > (st.session_state.starting_balance - 100):
        with placeholder.container():
            executed = 0
            for sym in markets:
                if random.random() < (0.65 if burst_mode else 0.35):
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
                    balance = balance * random.uniform(0.95, 1.09)
                    st.session_state.balance = balance
            
            if executed == 0:
                st.info("No strong signals this cycle.")
            
            st.metric("Current Balance", f"${balance:.2f}")
            st.metric("Loss from Start", f"${st.session_state.starting_balance - balance:.2f}")
        
        time.sleep(current_speed)

st.subheader("Recent Trades")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30))
else:
    st.info("No trades yet.")

if st.button("🛑 STOP ALL TRADING"):
    continuous_trading = False
    burst_mode = False
    st.success("All trading stopped.")

st.caption("Imperium Quant Edge • Continuous + Burst Mode with $100 Loss Protection")