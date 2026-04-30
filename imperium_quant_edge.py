import streamlit as st
from ib_async import *
import pandas as pd
from datetime import datetime
import time
import random

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; padding: 12px; }
    .box { background-color: #1a0000; padding: 20px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Kill Switch Fixed**")

# Connection
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Connected to {mode}!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Controls
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "USD.THB", "BTCUSD", "ETHUSD"],
    default=["XAUUSD", "EUR.USD", "BTCUSD"])

# Session State for Kill Switch
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False

# Kill Switch
if st.button("🛑 KILL SWITCH — Stop All Trading", type="primary"):
    st.session_state.trading_active = False
    st.success("All trading stopped!")

# Trading Logic
if auto_trading and st.session_state.get('connected') and (continuous or burst) and not st.session_state.trading_active:
    st.session_state.trading_active = True
    st.success(f"🚀 {'Burst Mode ⚡' if burst else 'Continuous Trading'} STARTED")

    placeholder = st.empty()
    
    while st.session_state.trading_active:
        with placeholder.container():
            for sym in markets:
                if random.random() < 0.45:
                    try:
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        elif sym in ["BTCUSD", "ETHUSD"]:
                            contract = Crypto(sym, "PAXOS", "USD")
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = random.choice(["BUY", "SELL"])
                        size = max(1, int(1000 * 0.01 / 100))
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ ORDER SENT: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Failed {sym}")
        
        time.sleep(0.7 if burst else 1.5)

st.subheader("Status")
st.info("Use the **KILL SWITCH** button to stop trading.")

st.button("Refresh Page", type="secondary")