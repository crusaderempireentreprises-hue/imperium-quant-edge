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
st.markdown("**Fast Kill Switch Version**")

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
        st.sidebar.success("✅ Connected!")
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
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "USD.THB", "BTCUSD"],
    default=["XAUUSD", "EUR.USD", "BTCUSD"])

# Kill Switch State
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False

# Big Kill Switch
if st.button("🛑 KILL SWITCH — STOP ALL TRADING", type="primary"):
    st.session_state.trading_active = False
    st.error("🛑 ALL TRADING STOPPED!")

# Trading
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    if not st.session_state.trading_active:
        st.session_state.trading_active = True
        st.success("Trading Started")

    placeholder = st.empty()
    
    for _ in range(20):   # Limited cycles to keep it responsive
        if not st.session_state.trading_active:
            st.warning("Trading Stopped")
            break
            
        with placeholder.container():
            for sym in markets:
                if random.random() < 0.5:
                    try:
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = random.choice(["BUY", "SELL"])
                        size = max(1, int(1000 * 0.01 / 100))
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ ORDER: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                    except:
                        pass
        time.sleep(0.6 if burst else 1.2)

st.subheader("Status")
st.info("Use the big red Kill Switch to stop trading instantly.")

st.button("Refresh App", type="secondary")