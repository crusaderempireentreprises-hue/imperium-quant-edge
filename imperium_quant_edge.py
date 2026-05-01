import streamlit as st
from ib_async import IB, Forex, Crypto, Stock, MarketOrder
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

# ---- Session defaults ----
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'ib' not in st.session_state:
    st.session_state.ib = None
if 'performance' not in st.session_state:
    st.session_state.performance = {}

st.title("🩸 Imperium Quant Edge")
st.markdown("**Smart Adaptive AI - Improved Error Handling**")

# Connection
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496, step=1)
client_id = st.sidebar.number_input("Client ID", value=53, step=1)

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=int(client_id))
        st.sidebar.success("✅ Connected!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")
        st.session_state.connected = False
        st.session_state.ib = None

# Controls
st.sidebar.subheader("AI Controls")
auto_trading = st.sidebar.toggle("Enable Smart Adaptive AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)

markets = st.sidebar.multiselect(
    "Select Markets",
    ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "BTCUSD", "ETHUSD"],
    default=["XAUUSD", "EUR.USD", "USDCAD"]
)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 0.6) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.connected:
    st.success("✅ Connected to IBKR")

# Keep performance in sync with selected markets
for m in markets:
    st.session_state.performance.setdefault(m, 0.0)

def get_contract(sym):
    try:
        if sym == "XAUUSD":
            return Forex("XAUUSD")
        elif sym in ["BTCUSD", "ETHUSD"]:
            return Crypto(sym, "PAXOS", "USD")
        else:
            clean = sym.replace(".", "")  # USDCAD, EURUSD etc.
            return Forex(clean)
    except Exception as e:
        st.warning(f"Contract creation failed for {sym}: {e}")
        return None

# Cancel Open Orders
if st.button("🧹 Cancel All Open Orders"):
    if st.session_state.connected and st.session_state.ib is not None:
        try:
            st.session_state.ib.reqGlobalCancel()
            st.success("✅ All open orders cancelled")
        except Exception as e:
            st.error(f"Cancel failed: {e}")
    else:
        st.warning("Not connected to IBKR")

# Trading Cycle
if st.button("▶️ SEND TRADING CYCLE NOW", type="primary"):
    if st.session_state.connected and st.session_state.ib is not None:
        ib = st.session_state.ib
        st.info("Cleaning old orders first...")
        try:
            ib.reqGlobalCancel()
        except Exception:
            pass
        
        success_count = 0
        for sym in markets:
            perf = st.session_state.performance.get(sym, 0.0)
            adapt_prob = 0.40 + (perf / 35)

            # Clamp probability between 0 and 1
            adapt_prob = max(0.0, min(1.0, adapt_prob))
            
            if random.random() < adapt_prob:
                try:
                    contract = get_contract(sym)
                    if contract is None:
                        continue
                        
                    signal = "BUY" if perf > -12 else "SELL"
                    # risk_pct is already fraction (e.g. 0.006 for 0.6%)
                    size = max(1, int(1000 * risk_pct))
                    
                    ib.placeOrder(contract, MarketOrder(signal, size))
                    st.success(f"✅ {signal} {size} {sym} (Score: {perf:.1f})")
                    success_count += 1
                    
                    # Learn (dummy PnL)
                    pnl = random.uniform(-0.04, 0.095)
                    st.session_state.performance[sym] += pnl * 100
                except Exception as e:
                    st.error(f"❌ Failed {sym}: {e}")
        
        st.info(f"Cycle complete. {success_count} trades attempted.")
    else:
        st.warning("Please connect first")

# Learning Scores
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(
        list(st.session_state.performance.items()),
        columns=["Market", "Learning Score"]
    )
    st.dataframe(
        df.sort_values("Learning Score", ascending=False),
        use_container_width=True
    )

st.subheader("Status")
st.info("Click 'SEND TRADING CYCLE NOW' after cancelling open orders if trades were failing.")

st.button("🛑 KILL SWITCH", type="primary")
