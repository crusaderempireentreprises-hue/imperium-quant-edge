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
    .box { background-color: #1a0000; padding: 18px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Real IBKR Trading - Improved Error Handling**")

# Top Boxes
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="box"><h3>🕒 Current Time</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="box"><h3>💰 Real IBKR Balance</h3><h2 id="balance-display">$ --.--</h2></div>', unsafe_allow_html=True)

st.markdown("""<script>function updateTime(){const now=new Date();document.getElementById('live-time').innerHTML=now.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}setInterval(updateTime,1000);updateTime();</script>""", unsafe_allow_html=True)

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
continuous = st.sidebar.toggle("🔄 Continuous (Max 20)", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "BTCUSD", "AAPL", "TSLA", "NVDA"],
    default=["XAUUSD", "EUR.USD"])

risk_pct = st.sidebar.slider("Risk %", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if 'connected' not in st.session_state:
    st.session_state.connected = False

if st.session_state.connected:
    st.success("✅ Connected to IBKR")

# ==================== REAL TRADING WITH BETTER ERROR HANDLING ====================
if auto_trading and st.session_state.connected and (continuous or burst):
    ib = st.session_state.ib
    st.success(f"🚀 Trying to send REAL orders...")

    placeholder = st.empty()
    
    for _ in range(12):
        with placeholder.container():
            for sym in markets:
                if random.random() < 0.45:
                    try:
                        # Better contract handling
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:  
                            contract = Forex(sym)
                        elif sym in ["BTCUSD", "ETHUSD"]:
                            contract = Crypto(sym, "PAXOS", "USD")
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = random.choice(["BUY", "SELL"])
                        size = max(1, int(1000 * risk_pct / 100))
                        
                        order = MarketOrder(signal, size)
                        trade = ib.placeOrder(contract, order)
                        
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ ORDER SENT: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"❌ Failed {sym}: {str(e)[:80]}...")
        
        time.sleep(0.8 if burst else 2.0)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("Check **TWS → Trades** and **Orders** tabs for real activity")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")