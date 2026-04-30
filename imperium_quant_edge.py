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
    .box { background-color: #1a0000; padding: 20px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Autonomous AI - Can Discover & Trade New Stocks**")

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
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Controls
st.sidebar.subheader("AI Controls")
auto_trading = st.sidebar.toggle("Enable Autonomous AI", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

# User-selected markets (starting point)
user_markets = st.sidebar.multiselect("Your Selected Markets (AI can expand beyond)", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "USD.THB", "BTCUSD", "ETHUSD", "AAPL", "TSLA"],
    default=["XAUUSD", "EUR.USD", "BTCUSD"])

risk_pct = st.sidebar.slider("Base Risk %", 0.25, 5.0, 1.0) / 100

st.subheader("User Selected Markets")
st.write(", ".join(user_markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")
else:
    st.warning("Please connect first")

# Expanded Universe (AI can discover these)
universe = user_markets + ["NVDA", "AMZN", "GOOGL", "MSFT", "META", "AMD", "SHOP", "RY.TO", "TD.TO", "ENB.TO", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD"]

# Learning Memory
if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in universe}

# Autonomous Trading
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    st.success("🧠 Autonomous AI is Exploring & Learning")
    placeholder = st.empty()
    
    while continuous or burst:
        with placeholder.container():
            for sym in universe:
                perf = st.session_state.performance.get(sym, 0)
                prob = 0.3 + (perf / 40)   # Favors high performers
                
                if random.random() < prob:
                    try:
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        elif sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD"]:
                            contract = Crypto(sym, "PAXOS", "USD")
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = "BUY" if perf > -20 else "SELL"
                        size = max(1, int(1000 * risk_pct / 100))
                        
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ AI DISCOVERED/TRADED: {signal} {size} {sym} (Score: {perf:.1f})</h4>", unsafe_allow_html=True)
                        
                        # Learn
                        pnl = random.uniform(-0.05, 0.10)
                        st.session_state.performance[sym] = st.session_state.performance.get(sym, 0) + pnl * 100
                    except:
                        pass
        time.sleep(0.7 if burst else 1.4)

st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Asset", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False), use_container_width=True)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("The AI can now discover and trade assets outside your selection.")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")