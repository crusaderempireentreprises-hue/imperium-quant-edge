import streamlit as st
from ib_async import *
import pandas as pd
import numpy as np
import talib
from datetime import datetime

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; padding: 10px; }
    .stButton>button:hover { background-color: #cc0000; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Multi-Market Automatic AI Trader**")

# ==================== CONNECTION SECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Successfully Connected to {mode}!")
        st.session_state.connected = True
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")
        st.session_state.connected = False

# Main App
if 'connected' not in st.session_state:
    st.session_state.connected = False

if st.session_state.connected:
    st.success("✅ Connected to IBKR - Ready to Trade")
else:
    st.warning("Please connect to IBKR using the sidebar first")

# Controls
auto_trading = st.toggle("🤖 Enable Auto Trading", value=False)

markets = st.multiselect("Markets", 
    ["XAUUSD (Gold)", "EUR.USD", "USD.CAD", "BTCUSD", "AAPL", "TSLA"],
    default=["XAUUSD (Gold)"])

risk_pct = st.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

if auto_trading and st.session_state.connected:
    st.success("Auto Trading is Active")

st.caption("Imperium Quant Edge - Windows Version")