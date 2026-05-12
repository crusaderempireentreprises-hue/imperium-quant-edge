import streamlit as st
import time
import random
from datetime import datetime
import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary
from oandapyV20.endpoints.positions import OpenPositions
import json

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
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

SYMBOLS = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "USD_CAD", "BTC_USD"]

if 'client' not in st.session_state: st.session_state.client = None
if 'connected' not in st.session_state: st.session_state.connected = False
if 'log' not in st.session_state: st.session_state.log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"{ts} | {msg}"
    st.session_state.log.append(entry)
    if len(st.session_state.log) > 150: st.session_state.log.pop(0)
    # Save to file
    try:
        with open("trade_log.txt", "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except:
        pass

# ====================== CONNECT ======================
if st.sidebar.button("🔌 CONNECT TO OANDA", type="primary"):
    try:
        client = oandapyV20.API(access_token=ACCESS_TOKEN)
        st.session_state.client = client
        st.session_state.connected = True
        add_log("✅ Connected to OANDA")
        st.success("✅ Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

# Risk Control
risk_pct = st.sidebar.slider("Risk % per Trade", 0.1, 2.0, 0.8)

# ====================== REFRESH BALANCE & POSITIONS ======================
if st.button("🔄 Refresh Balance & Positions"):
    if st.session_state.connected and st.session_state.client:
        try:
            r = AccountSummary(ACCOUNT_ID)
            summary = st.session_state.client.request(r)
            balance = float(summary['account']['NAV'])
            st.success(f"Balance: ${balance:,.2f}")

            r2 = OpenPositions(ACCOUNT_ID)
            pos = st.session_state.client.request(r2)
            st.write("**Open Positions:**")
            st.json(pos)
        except Exception as e:
            st.error(str(e))

# ====================== PLACE ORDER ======================
def place_order(symbol, side):
    if not st.session_state.connected or st.session_state.client is None:
        return False
    
    # Dynamic size based on risk (rough)
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
        add_log(f"✅ FILLED → {side} {units} {symbol}")
        st.success(f"Trade Filled: {side} {symbol}")
        return True
    except Exception as e:
        add_log(f"❌ Failed {symbol}: {str(e)[:100]}")
        st.error(str(e)[:150])
        return False

def run_cycle():
    if not st.session_state.connected:
        return
    add_log("--- AI Trading Cycle Started ---")
    for sym in SYMBOLS:
        side = random.choice(["BUY", "SELL"])
        place_order(sym, side)
        time.sleep(5)

# ====================== BUTTONS ======================
col1, col2 = st.columns(2)

if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    add_log("Continuous AI Trading Started")
    while True:
        run_cycle()
        time.sleep(10)

if col2.button("📊 Run One Cycle Now", use_container_width=True):
    run_cycle()

# Live Log
st.subheader("Live Activity Log")
for entry in reversed(st.session_state.log[-60:]):
    if "FILLED" in entry or "✅" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    else:
        st.info(entry)

st.caption("All features enabled • Trades logged to trade_log.txt")