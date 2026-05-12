import streamlit as st
import time
import random
from datetime import datetime
import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary

st.set_page_config(page_title="Imperium Quant Edge - OANDA", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - OANDA")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ff3333; }
    .stButton>button { background-color: #8B0000; color: white; border: 2px solid #ff3333; }
</style>
""", unsafe_allow_html=True)

# ====================== CREDENTIALS ======================
ACCOUNT_ID = "101-002-39303539-001"
ACCESS_TOKEN = "7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f"

SYMBOLS = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "USD_CAD"]

if 'client' not in st.session_state: st.session_state.client = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'log' not in st.session_state: st.session_state.log = []
if 'balance' not in st.session_state: st.session_state.balance = 0.0

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
        
        # Get balance
        r = AccountSummary(ACCOUNT_ID)
        summary = client.request(r)
        st.session_state.balance = float(summary['account']['NAV'])
        
        add_log("✅ Connected to OANDA")
        st.success(f"✅ Connected! Balance: ${st.session_state.balance:,.2f}")
    except Exception as e:
        st.error(f"Connection failed: {e}")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")
st.metric("Account Balance", f"${st.session_state.balance:,.2f}")

# ====================== PLACE ORDER ======================
def place_order(symbol, side):
    if not st.session_state.connected:
        add_log("Not connected")
        return False
    
    units = 25000 if side == "BUY" else -25000
    
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
        add_log(f"✅ SUCCESS → {side} 25,000 {symbol}")
        return True
    except Exception as e:
        add_log(f"❌ FAILED {symbol}: {str(e)[:120]}")
        return False

def run_cycle():
    if not st.session_state.connected:
        return
    add_log("--- Trading Cycle Started ---")
    for sym in SYMBOLS:
        side = random.choice(["BUY", "SELL"])
        place_order(sym, side)
        time.sleep(5)

# ====================== BUTTONS ======================
col1, col2 = st.columns(2)

if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    add_log("Continuous mode STARTED")
    while True:
        run_cycle()
        time.sleep(12)

if col2.button("📊 Run One Cycle Now", use_container_width=True):
    run_cycle()

# Live Log
st.subheader("Live Log")
for entry in reversed(st.session_state.log[-50:]):
    if "SUCCESS" in entry or "✅" in entry:
        st.success(entry)
    elif "FAILED" in entry or "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)

st.caption("OANDA • 25k units per trade • Check your OANDA platform for executions")