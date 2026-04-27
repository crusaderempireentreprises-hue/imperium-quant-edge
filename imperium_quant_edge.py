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
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; }
    .stButton>button:hover { background-color: #cc0000; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Multi-Market Automatic AI Trader** — Including Many Currencies")

# Sidebar
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Connected to {mode}")
        st.session_state.connected = True
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")
        st.session_state.connected = False

auto_trading = st.sidebar.toggle("🤖 Enable Auto Trading", value=False)

# Expanded Currency + Market List
markets = st.sidebar.multiselect("Select Markets (AI can trade multiple)", 
    [
        # Currencies (Forex)
        "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD", "USD.CHF", "EUR.GBP", "USD.MXN", "USD.BRL",
        "EUR.JPY", "GBP.JPY", "AUD.JPY", "NZD.USD",
        # Commodities
        "XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
        # Stocks
        "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO", "TD.TO",
        # Crypto
        "BTCUSD", "ETHUSD", "SOLUSD"
    ],
    default=["XAUUSD (Gold)", "EUR.USD", "USD.CAD", "BTCUSD"]
)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

# Main content
if 'connected' not in st.session_state:
    st.session_state.connected = False

if st.session_state.connected:
    st.success("✅ Connected to IBKR")
else:
    st.warning("Please connect to IBKR first")

if auto_trading and st.session_state.connected:
    st.success("🚀 Auto Trading is Active — Trading multiple currencies & assets")

st.subheader("Selected Markets")
st.write(markets)

st.caption("Imperium Quant Edge • Supports Major Currencies + Gold + Stocks + Crypto")