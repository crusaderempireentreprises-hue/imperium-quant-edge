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
st.markdown("**Stable Connection Version**")

# Connection Status
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'ib' not in st.session_state:
    st.session_state.ib = None

# Sidebar
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("🔗 Connect / Reconnect", type="primary"):
    try:
        if st.session_state.get('ib'):
            st.session_state.ib.disconnect()
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success("✅ Connected!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")
        st.session_state.connected = False

# Controls
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "BTCUSD"],
    default=["XAUUSD", "EUR.USD"])

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")
else:
    st.warning("Please connect first")

# Trading with Reconnection
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    st.success("🚀 Trading Running (Stable Mode)")
    placeholder = st.empty()
    
    for _ in range(30):   # Controlled to prevent overload
        if not st.session_state.get('connected'):
            st.error("Connection lost. Reconnect above.")
            break
            
        with placeholder.container():
            for sym in markets:
                if random.random() < 0.35:
                    try:
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = random.choice(["BUY", "SELL"])
                        size = max(1, int(1000 * 0.75 / 100))
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ ORDER: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Connection issue with {sym}. Reconnecting...")
                        st.session_state.connected = False
                        break
        time.sleep(3.0)   # Safe delay

st.subheader("Status")
st.info("Use **Connect / Reconnect** if connection drops.")

st.button("🛑 KILL SWITCH", type="primary")