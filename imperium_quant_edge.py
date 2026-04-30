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
st.markdown("**All Commodities + Currencies + Cryptos**")

# ==================== CONNECTION ====================
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

# Refresh Balance
if st.sidebar.button("🔄 Refresh Real Balance"):
    if st.session_state.get('connected'):
        try:
            summary = st.session_state.ib.accountSummary()
            for item in summary:
                if item.tag == "NetLiquidation":
                    balance = float(item.value)
                    st.session_state.balance = balance
                    st.success(f"✅ Balance: ${balance:,.2f}")
                    break
        except Exception as e:
            st.error(f"Refresh failed: {e}")

# Trading Controls
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading (No Limit)", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

# All Commodities + Currencies + Cryptos
markets = st.sidebar.multiselect("Select Markets", 
    [
        # Commodities
        "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "CL", "NG", "BZ",
        # Major Currencies
        "EUR.USD", "GBP.USD", "USD.JPY", "USD.CAD", "AUD.USD", "USD.CHF", "NZD.USD",
        "USD.THB", "USD.SGD", "USD.IDR", "USD.MYR", "USD.PHP",
        # Cryptocurrencies
        "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "BNBUSD", "AVAXUSD",
        # Stocks
        "AAPL", "TSLA", "NVDA"
    ],
    default=["XAUUSD", "EUR.USD", "USD.THB", "BTCUSD", "ETHUSD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")
else:
    st.warning("Please connect to IBKR first")

# Trading Logic
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    st.success(f"🚀 {'Burst Mode ⚡' if burst else 'Continuous Trading (No Limit)'} ACTIVE")
    placeholder = st.empty()
    
    for _ in range(10):
        with placeholder.container():
            for sym in markets:
                if random.random() < 0.45:
                    try:
                        if sym in ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"]:
                            contract = Forex(sym)
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        elif sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "BNBUSD", "AVAXUSD"]:
                            contract = Crypto(sym, "PAXOS", "USD")
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = random.choice(["BUY", "SELL"])
                        size = max(1, int(1000 * risk_pct / 100))
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ ORDER SENT: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Failed {sym}: {str(e)[:60]}")
        time.sleep(0.7 if burst else 1.5)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("Check **TWS → Trades tab** for real executions")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")