import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; }
    .stButton>button:hover { background-color: #cc0000; }
    .box { 
        background-color: #1a0000; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #ff3333; 
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Multi-Market Automatic AI Trader**")

# ==================== TOP TWO BOXES ====================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="box"><h3>🕒 Current Time (24hr)</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="box"><h3>💰 IBKR Balance</h3><h2 id="balance-display">$1,000.00</h2></div>', unsafe_allow_html=True)

# Live Time Update
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

# ==================== TRADING CONTROLS ====================
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

auto_trading = st.sidebar.toggle("🤖 Enable Auto Trading", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
     "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD",
     "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO",
     "BTCUSD", "ETHUSD", "SOLUSD"],
    default=["XAUUSD (Gold)", "EUR.USD", "BTCUSD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []

# ==================== TRADE LOG BOX ====================
st.subheader("📜 Trade Log")
trade_box = st.container()
with trade_box:
    st.markdown('<div class="box">', unsafe_allow_html=True)
    if st.session_state.trade_log:
        st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30), use_container_width=True)
    else:
        st.info("No trades yet. Enable Auto Trading.")
    st.markdown('</div>', unsafe_allow_html=True)

if auto_trading:
    st.success("🚀 Auto Trading is Active")
    # Simulation
    for _ in range(6):
        with st.spinner("AI analyzing..."):
            time.sleep(0.8)
            for sym in markets:
                if random.random() < 0.4:
                    signal = random.choice(["BUY", "SELL"])
                    st.markdown(f"<h4 style='color:#00ff88;'>✅ AI EXECUTED: {signal} of {sym}</h4>", unsafe_allow_html=True)
                    st.session_state.trade_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "symbol": sym,
                        "action": signal
                    })

st.button("🛑 KILL SWITCH — Stop All Trading", type="primary")

st.caption("Imperium Quant Edge • Custom Layout with Boxes")