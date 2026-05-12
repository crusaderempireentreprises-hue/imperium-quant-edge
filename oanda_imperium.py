import streamlit as st
import time
import random
from datetime import datetime
import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate

st.set_page_config(page_title="Imperium Quant Edge - OANDA", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - OANDA")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ff3333; }
    .stButton>button { background-color: #8B0000; color: white; border: 2px solid #ff3333; }
</style>
""", unsafe_allow_html=True)

# ====================== YOUR CREDENTIALS ======================
ACCOUNT_ID = "101-002-39303539-001"
ACCESS_TOKEN = "7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f"

SYMBOLS = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "USD_CAD"]

# Session State
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
        add_log("✅ Connected to OANDA")
        st.success("✅ Successfully connected to OANDA!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

# ====================== PLACE ORDER ======================
def place_order(symbol, side):
    if not st.session_state.connected:
        add_log("Not connected")
        return
    
    units = 25000 if side == "BUY" else -25000   # 25k units (roughly $25k-$35k notional)
    
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
        response = st.session_state.client.request(r)
        add_log(f"✅ {side} 25,000 {symbol} → Order Sent")
    except Exception as e:
        add_log(f"❌ Failed {symbol}: {str(e)[:100]}")

def run_cycle():
    if not st.session_state.connected:
        return
    add_log("--- Trading Cycle Started ---")
    for sym in SYMBOLS:
        try:
            side = random.choice(["BUY", "SELL"])
            place_order(sym, side)
            time.sleep(4)
        except:
            pass

# ====================== BUTTONS ======================
col1, col2 = st.columns(2)

if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    add_log("Continuous trading STARTED")
    while True:
        run_cycle()
        time.sleep(10)

if col2.button("📊 Run One Cycle Now", use_container_width=True):
    run_cycle()

# ====================== LIVE LOG ======================
st.subheader("Live Log")
for entry in reversed(st.session_state.log[-50:]):
    if "✅" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)

st.caption("Imperium Quant Edge • OANDA Version • Ready for Canada & Abroad")