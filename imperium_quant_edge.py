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
st.markdown("**Real IBKR Trading**")

# Top Boxes
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="box"><h3>🕒 Current Time (24hr)</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="box"><h3>💰 Real IBKR Balance</h3><h2 id="balance-display">$ --.--</h2></div>', unsafe_allow_html=True)

st.markdown("""
<script>
function updateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('live-time').innerHTML = timeStr;
}
setInterval(updateTime, 1000);
updateTime();
</script>
""", unsafe_allow_html=True)

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
        st.success("Connection successful!")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")

# Refresh Balance Button
if st.sidebar.button("🔄 Refresh Real Balance"):
    if st.session_state.get('connected') and st.session_state.get('ib'):
        try:
            summary = st.session_state.ib.accountSummary()
            for item in summary:
                if item.tag == "NetLiquidation":
                    balance = float(item.value)
                    st.session_state.balance = balance
                    st.success(f"✅ Balance Updated: ${balance:,.2f}")
                    break
        except Exception as e:
            st.error(f"Balance refresh failed: {e}")

# Controls
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous (Max 20)", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AAPL", "TSLA"],
    default=["XAUUSD", "EUR.USD"])

risk_pct = st.sidebar.slider("Risk %", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")
    if st.session_state.get('balance'):
        st.markdown(f'<div class="box"><h3>💰 Real Balance: ${st.session_state.balance:,.2f}</h3></div>', unsafe_allow_html=True)
else:
    st.warning("Click 'Connect to IBKR' then 'Refresh Real Balance'")

# Trading Logic (simplified)
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    st.success("🚀 Auto Trading Active")
    # ... (your trading logic here)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("Check TWS → Trades tab for real activity")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")