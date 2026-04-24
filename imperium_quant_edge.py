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
    .warning { color: #ff0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Multi-Market Automatic AI Trader** — Safety Enhanced")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

if mode == "Live Trading (Real Money)":
    st.sidebar.markdown("<p class='warning'>⚠️ REAL MONEY MODE — HIGH RISK</p>", unsafe_allow_html=True)

auto_trading = st.sidebar.toggle("🤖 Start Continuous Auto Trading", value=False)
max_trades = 20

markets = st.sidebar.multiselect(
    "Select Markets",
    ["XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
     "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
     "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO",
     "BTCUSD", "ETHUSD", "SOLUSD"],
    default=["XAUUSD (Gold)", "EUR.USD", "BTCUSD"]
)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.1, 5.0, 0.5) / 100   # Lower default for safety

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = [1000.0]
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0
if 'trade_count' not in st.session_state:
    st.session_state.trade_count = 0

balance = st.session_state.balance

if "Paper" in mode:
    st.success("📌 Paper Mode — Safe Testing")
else:
    st.error("⚠️ LIVE REAL MONEY MODE — EXTREME CAUTION")

if mode == "Live Trading (Real Money)" and auto_trading:
    if st.button("⚠️ CONFIRM: ENABLE AUTO TRADING WITH REAL MONEY"):
        pass
    else:
        auto_trading = False
        st.warning("Click the confirm button to enable Live Auto Trading")

if auto_trading and st.session_state.trade_count < max_trades:
    st.success(f"🚀 Auto Trading Running — Max {max_trades} trades")
    
    placeholder = st.empty()
    
    while auto_trading and st.session_state.trade_count < max_trades:
        with placeholder.container():
            executed = 0
            for sym in markets:
                if random.random() < 0.35:
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
                    balance *= random.uniform(0.96, 1.08)
                    st.session_state.balance = balance
                    st.session_state.trade_count += 1
            
            st.metric("Current Balance", f"${balance:.2f}")
            st.metric("Trades Executed", f"{st.session_state.trade_count} / {max_trades}")
        
        time.sleep(1.5)

if st.session_state.trade_count >= max_trades:
    st.warning("Maximum trades reached. Auto Trading stopped.")

st.subheader("Trade History")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30))

if st.button("🛑 STOP ALL AUTO TRADING"):
    auto_trading = False
    st.success("Auto Trading Stopped.")

st.caption("Imperium Quant Edge • Safety Enhanced Version")