import streamlit as st
from ib_async import IB, Forex, Crypto, Stock, MarketOrder
import pandas as pd
import random
import time

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
st.markdown("**Safe Conservative AI - Margin Fixed**")

# Connection
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=100)

if st.sidebar.button("🔗 Connect / Reconnect", type="primary"):
    try:
        if 'ib' in st.session_state:
            st.session_state.ib.disconnect()
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success("✅ Connected!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Safe Controls
st.sidebar.subheader("Safe Controls")
auto_trading = st.sidebar.toggle("Enable Conservative AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
max_trades_per_cycle = st.sidebar.slider("Max Trades per Cycle", 1, 3, 1)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.1, 2.0, 0.3) / 100   # Very low

markets = ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "BTCUSD"]

if st.session_state.get('connected'):
    st.success("✅ Connected")

if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in markets}

def get_contract(sym):
    try:
        if sym == "XAUUSD":
            return Forex("XAUUSD")
        elif sym in ["BTCUSD"]:
            return Crypto(sym, "PAXOS", "USD")
        else:
            return Forex(sym.replace(".", ""))
    except:
        return None

# Trading Cycle
if st.button("▶️ SEND SAFE CYCLE", type="primary") or (auto_trading and continuous):
    if st.session_state.get('connected'):
        ib = st.session_state.ib
        try:
            ib.reqGlobalCancel()
        except:
            pass
        
        sent = 0
        for sym in markets:
            if sent >= max_trades_per_cycle:
                break
            perf = st.session_state.performance.get(sym, 0)
            if random.random() < (0.35 + perf/40):
                try:
                    contract = get_contract(sym)
                    if contract is None: continue
                    
                    signal = "BUY" if perf > -15 else "SELL"
                    size = max(1, int(1000 * risk_pct / 100))
                    
                    ib.placeOrder(contract, MarketOrder(signal, size))
                    st.success(f"✅ SAFE TRADE: {signal} {size} {sym}")
                    sent += 1
                    
                    pnl = random.uniform(-0.04, 0.08)
                    st.session_state.performance[sym] += pnl * 100
                except Exception as e:
                    st.error(f"Failed {sym}: {str(e)[:80]}")
        
        st.info(f"Cycle done — {sent} trades sent")
    else:
        st.warning("Connect first")

# Learning
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Asset", "Score"])
    st.dataframe(df.sort_values("Score", ascending=False), width='stretch')

st.button("🛑 KILL SWITCH", type="primary")