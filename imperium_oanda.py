import streamlit as st
import time
import random
from datetime import datetime
import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary
from oandapyV20.endpoints.positions import OpenPositions

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

# Connect
if st.sidebar.button("🔌 CONNECT TO OANDA", type="primary"):
    try:
        client = oandapyV20.API(access_token=ACCESS_TOKEN)
        st.session_state.client = client
        st.session_state.connected = True
        add_log("✅ Connected")
        st.success("Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

# Show Open Positions
if st.button("🔄 Refresh Balance & Positions"):
    if st.session_state.connected:
        try:
            r = AccountSummary(ACCOUNT_ID)
            summary = st.session_state.client.request(r)
            balance = float(summary['account']['NAV'])
            st.success(f"Balance: ${balance:,.2f}")

            r2 = OpenPositions(ACCOUNT_ID)
            positions = st.session_state.client.request(r2)
            st.write("**Open Positions:**", positions)
        except Exception as e:
            st.error(str(e))

# Place Order
def place_order(symbol, side):
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
        r = OrderCreate(ACCOUNT_ID, data=data)
        resp = st.session_state.client.request(r)
        add_log(f"✅ {side} 10k {symbol} Filled")
        st.success(f"Trade Executed: {side} {symbol}")
    except Exception as e:
        add_log(f"❌ {symbol}: {str(e)[:100]}")
        st.error(str(e))

col1, col2 = st.columns(2)
if col1.button("🚀 START CONTINUOUS", type="primary", use_container_width=True):
    while True:
        for sym in ["EUR_USD", "GBP_USD"]:
            place_order(sym, random.choice(["BUY", "SELL"]))
            time.sleep(6)

if col2.button("📊 Run One Cycle Now", use_container_width=True):
    for sym in ["EUR_USD", "GBP_USD"]:
        place_order(sym, random.choice(["BUY", "SELL"]))
        time.sleep(4)

st.subheader("Log")
for entry in reversed(st.session_state.log[-40:]):
    if "✅" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)