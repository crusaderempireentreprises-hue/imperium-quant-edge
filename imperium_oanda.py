import streamlit as st
import time
import random
from datetime import datetime
import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary

st.set_page_config(page_title="Imperium Quant Edge - OANDA", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - OANDA")

st.markdown("<style>.stApp { background-color: #0a0a0a; color: #ff3333; }</style>", unsafe_allow_html=True)

ACCOUNT_ID = "101-002-39303539-001"
ACCESS_TOKEN = "7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f"

if 'client' not in st.session_state: st.session_state.client = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'log' not in st.session_state: st.session_state.log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append(f"{ts} | {msg}")
    if len(st.session_state.log) > 100: st.session_state.log.pop(0)

# ====================== CONNECT ======================
if st.sidebar.button("🔌 CONNECT TO OANDA", type="primary"):
    try:
        client = oandapyV20.API(access_token=ACCESS_TOKEN)
        st.session_state.client = client
        st.session_state.connected = True
        add_log("✅ Connected successfully")
        st.success("✅ Connected to OANDA!")
    except Exception as e:
        st.error(f"Connection failed: {e}")
        add_log(f"❌ Connection error: {e}")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

# ====================== PLACE ORDER ======================
def place_order(symbol, side):
    if not st.session_state.connected or st.session_state.client is None:
        add_log("Not connected or client is None")
        st.warning("Please connect first")
        return
    
    units = 10000 if side == "BUY" else -10000
    
    data = {
        "order": {
            "units": str(units),
            "instrument": symbol,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }
    
    try:
        add_log(f"→ Sending {side} 10k {symbol}...")
        r = OrderCreate(ACCOUNT_ID, data=data)
        response = st.session_state.client.request(r)
        add_log(f"✅ SUCCESS: {side} 10k {symbol}")
        st.success(f"Trade Executed: {side} {symbol}")
    except Exception as e:
        add_log(f"❌ Failed {symbol}: {str(e)[:120]}")
        st.error(f"Order Failed: {str(e)[:100]}")

def run_cycle():
    if not st.session_state.connected or st.session_state.client is None:
        st.warning("Please connect first")
        return
    add_log("--- Cycle Started ---")
    for sym in ["EUR_USD", "GBP_USD"]:
        side = random.choice(["BUY", "SELL"])
        place_order(sym, side)
        time.sleep(5)

# Buttons
col1, col2 = st.columns(2)

if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    while True:
        run_cycle()
        time.sleep(10)

if col2.button("📊 Run One Cycle Now", use_container_width=True):
    run_cycle()

# Log
st.subheader("Live Log")
for entry in reversed(st.session_state.log[-50:]):
    if "SUCCESS" in entry or "✅" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)