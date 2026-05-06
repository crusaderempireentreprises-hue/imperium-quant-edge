import streamlit as st
import random
import time
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - TEST MODE")

st.markdown("<style>.stApp { background-color: #0a0a0a; color: #ff3333; }</style>", unsafe_allow_html=True)

# Session State
if 'ib' not in st.session_state: st.session_state.ib = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'log' not in st.session_state: st.session_state.log = []

def add_log(msg):
    ts = time.strftime('%H:%M:%S')
    st.session_state.log.append(f"{ts} | {msg}")
    if len(st.session_state.log) > 100: st.session_state.log.pop(0)

# Sidebar
st.sidebar.header("Controls")
port = st.sidebar.selectbox("Mode", [7497, 7496], 
    format_func=lambda x: "Paper Trading (7497)" if x==7497 else "Live (7496)")
client_id = st.sidebar.number_input("Client ID", value=9999, step=1)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        add_log("✅ Connected")
        st.success("✅ Connected to IBKR!")
    except Exception as e:
        add_log(f"❌ Connect error: {e}")
        st.error(str(e))

if st.sidebar.button("🛑 CANCEL ALL OPEN ORDERS"):
    if st.session_state.connected:
        st.session_state.ib.reqGlobalCancel()
        add_log("🛑 Global Cancel sent")
        st.success("All open orders cancelled")

# Test Order Button
if st.button("🔥 PLACE TEST ORDER (EUR.USD)", type="primary", use_container_width=True):
    if not st.session_state.connected:
        st.error("Not connected!")
    else:
        try:
            ib = st.session_state.ib
            ib.reqGlobalCancel()
            contract = Forex("EURUSD")
            ib.qualifyContracts(contract)
            
            order = MarketOrder("BUY", 25000)   # Big enough size
            trade = ib.placeOrder(contract, order)
            add_log("✅ TEST ORDER SENT: BUY 25000 EUR.USD")
            st.success("Test order sent! Check TWS now.")
        except Exception as e:
            add_log(f"❌ Test order failed: {e}")
            st.error(str(e))

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

log_container = st.empty()

# Live Log
st.subheader("Debug Log")
for entry in reversed(st.session_state.log[-40:]):
    if "✅" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)

st.caption("Click 'PLACE TEST ORDER' and check if anything appears in TWS/IBKR")