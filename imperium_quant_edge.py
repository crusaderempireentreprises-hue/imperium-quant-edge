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
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; padding: 12px; }
    .box { background-color: #1a0000; padding: 20px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Optimized Trading Simulation**")

# Top Time Box
st.markdown('<div class="box"><h3>🕒 Current Time (24hr)</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)

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

# Sidebar Controls
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AAPL", "TSLA"],
    default=["XAUUSD", "EUR.USD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

# Session State
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'balance' not in st.session_state:
    st.session_state.balance = 1000000.0

# Trading Logic
if auto_trading and (continuous or burst):
    st.success(f"🚀 {'Burst Mode ⚡' if burst else 'Continuous Trading'} ACTIVE")
    placeholder = st.empty()
    
    for _ in range(15 if burst else 8):
        with placeholder.container():
            executed = 0
            for sym in markets:
                # Optimized signal logic
                trend = random.uniform(-1, 1)
                volatility = random.uniform(0.4, 1.3)
                signal_strength = abs(trend) * volatility
                
                if signal_strength > 0.45:
                    signal = "BUY" if trend > 0 else "SELL"
                    size = max(1, int(st.session_state.balance * risk_pct * 0.8))
                    
                    pnl = random.uniform(-0.035, 0.065) * volatility
                    
                    st.markdown(f"<h4 style='color:#00ff88;'>✅ TRADE: {signal} {size} {sym} (P&L: {pnl*100:+.2f}%) </h4>", unsafe_allow_html=True)
                    
                    st.session_state.trade_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "symbol": sym,
                        "action": signal,
                        "size": size,
                        "pnl": round(pnl*100, 2)
                    })
                    
                    st.session_state.balance *= (1 + pnl)
                    executed += 1
            
            st.metric("Current Balance", f"${st.session_state.balance:,.2f}")
            st.metric("Trades This Cycle", executed)
        
        time.sleep(0.5 if burst else 1.2)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    if st.session_state.trade_log:
        st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(30), use_container_width=True)
    else:
        st.info("No trades yet. Enable Auto Trading.")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")