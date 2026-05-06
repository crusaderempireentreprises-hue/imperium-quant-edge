import streamlit as st
import time
import random
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - SIMPLE MODE")

st.markdown("<style>.stApp { background-color: #0a0a0a; color: #ff3333; }</style>", unsafe_allow_html=True)

if 'ib' not in st.session_state: st.session_state.ib = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'log' not in st.session_state: st.session_state.log = []

def add_log(msg):
    ts = time.strftime('%H:%M:%S')
    st.session_state.log.append(f"{ts} | {msg}")
    if len(st.session_state.log) > 80: st.session_state.log.pop(0)

# Sidebar
st.sidebar.header("Controls")
port = st.sidebar.selectbox("Mode", [7497, 7496], 
    format_func=lambda x: "Paper (7497)" if x==7497 else "Live (7496)")
client_id = st.sidebar.number_input("Client ID", value=9999, step=1)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        add_log("✅ Connected")
        st.success("✅ Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

if st.sidebar.button("🛑 CANCEL ALL OPEN ORDERS"):
    if st.session_state.connected:
        st.session_state.ib.reqGlobalCancel()
        add_log("🛑 Cancelled all orders")
        st.success("Cancelled!")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

# Live Log
st.subheader("Live Log")

def execute_cycle():
    if not st.session_state.connected:
        st.warning("Not connected")
        return
    
    ib = st.session_state.ib
    ib.reqGlobalCancel()
    
    sym = "EUR.USD"
    try:
        contract = Forex("EURUSD")
        ib.qualifyContracts(contract)
        
        size = 25000
        signal = random.choice(["BUY", "SELL"])
        
        order = MarketOrder(signal, size)
        ib.placeOrder(contract, order)
        
        st.success(f"✅ SENT → {signal} {size:,} {sym}")
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)[:100]}")

# Buttons
col1, col2 = st.columns(2)

if col1.button("🚀 START CONTINUOUS", type="primary", use_container_width=True):
    st.info("Continuous mode started - check TWS")
    while True:
        execute_cycle()
        time.sleep(12)

if col2.button("📊 Run One Cycle", use_container_width=True):
    execute_cycle()

st.caption("Click 'Run One Cycle' first, then check TWS Orders tab")