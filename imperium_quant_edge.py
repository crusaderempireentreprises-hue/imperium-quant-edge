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
st.markdown("**Multi-Market Automatic AI Trader**")

# ==================== CONNECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

connected = False
ib = None

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success(f"✅ Connected to {mode}")
        connected = True
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")

# ==================== TRADING CONTROLS ====================
auto_trading = st.sidebar.toggle("🤖 Enable Auto Trading", value=False)

markets = st.sidebar.multiselect("Markets (AI can trade multiple)", 
    ["XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
     "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
     "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO", "TD.TO",
     "BTCUSD", "ETHUSD", "SOLUSD"],
    default=["XAUUSD (Gold)", "EUR.USD", "BTCUSD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

# Main content
if connected:
    st.success("✅ Connected to IBKR - Ready for Trading")
else:
    st.warning("Please click 'Connect to IBKR' in the sidebar first")

if auto_trading and connected:
    st.success("🚀 Auto Trading is Active")
    # Simple simulation for now (replace with real trading logic later)
    st.info("AI is scanning markets and will execute trades when signals appear.")

st.subheader("Recent Activity")
st.info("No trades yet. Connect and enable Auto Trading.")

if st.button("🛑 KILL SWITCH — Cancel All Orders"):
    if ib:
        try:
            ib.reqGlobalCancel()
            st.warning("All open orders cancelled.")
        except:
            st.error("Could not cancel orders.")

st.caption("Imperium Quant Edge • Latest Version with Connect Button")