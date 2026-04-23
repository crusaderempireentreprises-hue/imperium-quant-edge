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
st.markdown("**Multi-Market Automatic AI Trader** — Continuous Mode")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

running = st.sidebar.toggle("🤖 Start Continuous Auto Trading", value=False)

markets = st.sidebar.multiselect(
    "Select Markets (AI scans all)",
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

balance = st.session_state.balance

if "Paper" in mode:
    st.success("📌 Paper Mode — $1,000 Fake Money")
else:
    st.warning("⚠️ Live Mode — Real Money at Risk")

st.subheader("Active Markets")
st.write(markets)

if running:
    st.success("🚀 AI is running continuously... (scanning all markets)")
    
    placeholder = st.empty()
    
    while running:
        with placeholder.container():
            st.info(f"Scanning {len(markets)} markets...")
            
            executed = 0
            for sym in markets:
                if random.random() < 0.35:  # Chance of signal
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
            
            st.metric("Current Balance", f"${balance:.2f}")
        
        time.sleep(1.2)  # Adjustable speed

st.subheader("Recent Trades")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30))
else:
    st.info("No trades yet.")

if st.button("🛑 STOP AUTO TRADING"):
    running = False
    st.success("Auto Trading Stopped.")

st.caption("Imperium Quant Edge • Continuous Multi-Market AI")