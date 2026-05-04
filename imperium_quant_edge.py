import streamlit as st
import random
import time
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - FIXED")

st.markdown("<style>.stApp { background-color: #0a0a0a; color: #ff3333; }</style>", unsafe_allow_html=True)

# Session State
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
    format_func=lambda x: "🟢 Paper Trading (7497)" if x==7497 else "🔴 Live Trading (7496)")
client_id = st.sidebar.number_input("Client ID (use high number)", value=9999, step=1)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        add_log("✅ Connected")
        st.success("Connected!")
    except Exception as e:
        add_log(f"❌ Connect failed: {e}")
        st.error(str(e))

# Cancel Button
if st.sidebar.button("🛑 CANCEL ALL OPEN ORDERS", type="secondary"):
    if st.session_state.connected:
        st.session_state.ib.reqGlobalCancel()
        add_log("🛑 All open orders cancelled")
        st.success("Cancelled all orders!")

markets = ["EUR.USD", "GBP.USD", "USDCAD", "USD.JPY"]
risk_pct = st.sidebar.slider("Risk % per Trade", 0.5, 5.0, 1.5) / 100

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

log_container = st.empty()

def get_contract(sym):
    return Forex(sym.replace(".", ""))

def get_min_size(sym):
    if sym in ["EUR.USD", "GBP.USD"]: return 20000
    if sym in ["USDCAD", "USD.JPY"]: return 25000
    return 10000

def execute_cycle():
    if not st.session_state.connected:
        add_log("Not connected")
        return
    
    ib = st.session_state.ib
    ib.reqGlobalCancel()
    add_log("--- New Cycle Started ---")
    
    for sym in markets:
        try:
            add_log(f"Processing {sym}")
            contract = get_contract(sym)
            ib.qualifyContracts(contract)
            
            size = max(get_min_size(sym), int(25000 * risk_pct))
            signal = random.choice(["BUY", "SELL"])
            
            order = MarketOrder(signal, size)
            add_log(f"Placing {signal} {size:,} {sym}")
            trade = ib.placeOrder(contract, order)
            
            add_log(f"✅ ORDER SUBMITTED: {signal} {size:,} {sym}")
            time.sleep(4)
            
        except Exception as e:
            add_log(f"❌ {sym}: {str(e)[:100]}")

# Buttons
col1, col2 = st.columns(2)
if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    add_log("Continuous mode STARTED")
    while True:
        execute_cycle()
        time.sleep(10)

if col2.button("📊 Run One Cycle", use_container_width=True):
    execute_cycle()

# Live Log
st.subheader("Live Log")
for entry in reversed(st.session_state.log[-35:]):
    if "✅ ORDER SUBMITTED" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)