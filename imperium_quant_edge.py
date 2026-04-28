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
    .box { background-color: #1a0000; padding: 25px; border-radius: 12px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Real IBKR Balance Fixed**")

# Top Boxes
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="box"><h3>🕒 Current Time</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)
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
        st.success("Connection successful! Click Refresh Balance below")
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Refresh Balance
if st.sidebar.button("🔄 Refresh Real Balance", type="primary"):
    if st.session_state.get('connected') and st.session_state.get('ib'):
        try:
            summary = st.session_state.ib.accountSummary()
            for item in summary:
                if item.tag == "NetLiquidation":
                    balance = float(item.value)
                    st.session_state.balance = balance
                    st.markdown(f'<div class="box"><h2>💰 ${balance:,.2f}</h2></div>', unsafe_allow_html=True)
                    st.success("Balance Updated!")
                    break
        except Exception as e:
            st.error(f"Balance fetch failed: {e}")
    else:
        st.warning("Please connect first")

st.subheader("Active Markets")
markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AAPL", "TSLA"],
    default=["XAUUSD", "EUR.USD"])

st.write(", ".join(markets))

st.button("🛑 KILL SWITCH", type="primary")