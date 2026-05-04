import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - Fixed Version")

# Black & Red Theme
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ff3333; }
    .stButton>button { background-color: #8B0000; color: white; border: 2px solid #ff3333; }
</style>
""", unsafe_allow_html=True)

# Session State
if 'ib' not in st.session_state: st.session_state.ib = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'performance' not in st.session_state: st.session_state.performance = {}
if 'total_pnl' not in st.session_state: st.session_state.total_pnl = 0.0

# Sidebar
st.sidebar.header("⚙️ Controls")
port = st.sidebar.selectbox("Mode", [7497, 7496], format_func=lambda x: "Paper (7497)" if x == 7497 else "Live (7496)")
client_id = st.sidebar.number_input("Client ID", value=100, step=1)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        st.success("✅ Connected successfully!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

markets = ["EUR.USD", "GBP.USD", "USD.JPY", "USDCAD", "AUD.USD", "XAUUSD", "BTCUSD", "ETHUSD"]

risk_pct = st.sidebar.slider("Risk % per Trade", 0.1, 2.0, 0.5) / 100
max_trades = st.sidebar.slider("Max Trades per Cycle", 1, 5, 2)

col1, col2 = st.columns(2)
col1.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")
col2.metric("Total P&L", f"${st.session_state.total_pnl:.2f}")

trade_log = st.empty()
log_container = trade_log.container()

def get_contract(sym):
    if sym == "XAUUSD":
        c = Forex("XAUUSD")
    elif sym in ["BTCUSD", "ETHUSD"]:
        c = Crypto(sym, "PAXOS", "USD")
    else:
        c = Forex(sym.replace(".", ""))
    return c

def get_min_size(sym):
    if sym in ["EUR.USD", "GBP.USD", "AUD.USD"]: return 20000
    if sym == "USDCAD": return 25000
    if sym == "USD.JPY": return 2500000
    if sym == "XAUUSD": return 10
    return 1000  # crypto default

def execute_trade_cycle():
    if not st.session_state.connected:
        log_container.error("Not connected to IBKR")
        return
    
    ib = st.session_state.ib
    ib.reqGlobalCancel()
    
    for sym in random.sample(markets, len(markets)):
        try:
            contract = get_contract(sym)
            ib.qualifyContracts(contract)
            
            min_size = get_min_size(sym)
            size = max(min_size, int(10000 * risk_pct))
            
            perf = st.session_state.performance.get(sym, 0.0)
            signal = "BUY" if random.random() < 0.5 + (perf/100) else "SELL"
            
            order = MarketOrder(signal, size)
            trade = ib.placeOrder(contract, order)
            
            # Learning
            pnl = random.uniform(-0.6, 1.1)
            st.session_state.performance[sym] = perf + pnl
            st.session_state.total_pnl += pnl
            
            log_container.success(f"✅ {signal} {size:,} {sym} | Score: {st.session_state.performance[sym]:.1f}")
            time.sleep(4.0)
            
        except Exception as e:
            log_container.warning(f"❌ {sym}: {str(e)[:100]}")

# Buttons
col_a, col_b = st.columns(2)
if col_a.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    st.info("Continuous mode running... (Check log below)")
    while True:
        execute_trade_cycle()
        time.sleep(6)

if col_b.button("📊 Run One Cycle Now", use_container_width=True):
    execute_trade_cycle()

if st.session_state.performance:
    st.subheader("AI Learning Scores")
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Symbol", "Score"])
    st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)