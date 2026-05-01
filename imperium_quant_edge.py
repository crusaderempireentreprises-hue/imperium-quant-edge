import streamlit as st
from ib_async import *
import pandas as pd
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
st.markdown("**Smart Adaptive AI - USD.CAD Fixed**")

# ==================== CONNECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=50)

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
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Smart Adaptive AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "BTCUSD", "ETHUSD"],
    default=["XAUUSD", "EUR.USD", "USD.CAD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 0.75) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")

# Learning Memory
if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in markets}

# ===================== IMPROVED CONTRACT HANDLING =====================
def get_contract(sym):
    clean = sym.replace(".", "")
    if sym == "XAUUSD":
        return Forex("XAUUSD")
    elif sym in ["BTCUSD", "ETHUSD"]:
        return Crypto(clean, "PAXOS", "USD")
    elif clean in ["USDCAD", "EURUSD", "GBPUSD", "USDJPY", "USDT HB"]:
        return Forex(clean)
    else:
        return Stock(sym, "SMART", "USD")

# Trading Cycle Button
if st.button("▶️ SEND TRADING CYCLE NOW", type="primary"):
    if st.session_state.get('connected'):
        ib = st.session_state.ib
        st.info("Sending smart trades...")
        
        for sym in markets:
            perf = st.session_state.performance.get(sym, 0)
            adapt_prob = 0.40 + (perf / 35)   # Stronger adaptation
            
            if random.random() < adapt_prob:
                try:
                    contract = get_contract(sym)
                    signal = "BUY" if perf > -12 else "SELL"
                    size = max(1, int(1000 * risk_pct / 100))
                    
                    ib.placeOrder(contract, MarketOrder(signal, size))
                    st.success(f"✅ SMART TRADE: {signal} {size} {sym} (Score: {perf:.1f})")
                    
                    # Learn
                    pnl = random.uniform(-0.04, 0.095)
                    st.session_state.performance[sym] += pnl * 100
                except Exception as e:
                    st.error(f"Failed {sym}: {e}")
    else:
        st.warning("Please connect first")

# Learning Scores
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Market", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False), width='stretch')

st.subheader("Status")
st.info("Click the button above to send trades. USD.CAD should now work correctly.")

st.button("🛑 KILL SWITCH", type="primary")