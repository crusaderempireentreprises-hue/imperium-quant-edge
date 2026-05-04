import streamlit as st
import random
import time
from ib_async import IB, Forex, MarketOrder

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE - DEBUG MODE")

st.markdown(
    """
    <style>
        .stApp { 
            background-color: #0a0a0a; 
            color: #ff3333; 
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Session State
# -------------------------
if 'ib' not in st.session_state:
    st.session_state.ib = None

if 'connected' not in st.session_state:
    st.session_state.connected = False

if 'log' not in st.session_state:
    st.session_state.log = []

if 'continuous' not in st.session_state:
    st.session_state.continuous = False

if 'last_cycle_time' not in st.session_state:
    st.session_state.last_cycle_time = 0.0


def add_log(msg):
    timestamp = time.strftime('%H:%M:%S')
    st.session_state.log.append(f"{timestamp} | {msg}")

    if len(st.session_state.log) > 100:
        st.session_state.log.pop(0)


# -------------------------
# Sidebar
# -------------------------
st.sidebar.header("Controls")

port = st.sidebar.selectbox(
    "Mode",
    [7497, 7496],
    format_func=lambda x: "Paper Trading (7497)" if x == 7497 else "Live Trading (7496)"
)

client_id = int(
    st.sidebar.number_input("Client ID", value=100, step=1)
)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect("127.0.0.1", port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True

        add_log("✅ Successfully connected to IBKR")
        st.success("Connected to IBKR!")

    except Exception as e:
        st.session_state.connected = False
        st.session_state.ib = None

        add_log(f"❌ Connection failed: {e}")
        st.error(f"Connection failed: {e}")


# -------------------------
# Cancel Open Orders
# -------------------------
if st.sidebar.button("🛑 CANCEL ALL OPEN ORDERS", type="secondary"):
    if st.session_state.connected and st.session_state.ib is not None:
        try:
            st.session_state.ib.reqGlobalCancel()
            add_log("🛑 Global Cancel sent - All open orders cancelled")
            st.success("All open orders cancelled!")
        except Exception as e:
            add_log(f"❌ Cancel failed: {e}")
            st.error(f"Cancel failed: {e}")
    else:
        st.warning("Not connected to IBKR")


# -------------------------
# Trading Settings
# -------------------------
markets = ["EUR.USD", "GBP.USD", "USDCAD", "XAUUSD"]

risk_pct = (
    st.sidebar.slider("Risk % per Trade", 0.5, 5.0, 2.0) / 100
)

st.metric(
    "Status",
    "🟢 Connected" if st.session_state.connected else "🔴 Disconnected"
)


# -------------------------
# Contract Builder
# -------------------------
def get_contract(sym):
    if sym == "XAUUSD":
        return Forex("XAUUSD")

    return Forex(sym.replace(".", ""))


# -------------------------
# Trading Cycle
# -------------------------
def execute_cycle():
    if not st.session_state.connected or st.session_state.ib is None:
        add_log("Not connected")
        return

    ib = st.session_state.ib

    add_log("--- Starting Trading Cycle ---")

    try:
        ib.reqGlobalCancel()
        add_log("Auto Global Cancel executed")
    except Exception as e:
        add_log(f"❌ Global cancel failed: {e}")

    for sym in markets:
        try:
            add_log(f"→ Processing {sym}")

            contract = get_contract(sym)
            ib.qualifyContracts(contract)

            size = max(25000, int(25000 * risk_pct))
            signal = random.choice(["BUY", "SELL"])

            add_log(f"Placing {signal} {size:,} {sym}")

            order = MarketOrder(signal, size)
            ib.placeOrder(contract, order)

            add_log(f"✅ ORDER SUBMITTED: {signal} {size:,} {sym}")

            time.sleep(1.0)

        except Exception as e:
            add_log(f"❌ ERROR on {sym}: {str(e)[:100]}")


# -------------------------
# Buttons
# -------------------------
col1, col2, col3 = st.columns(3)

if col1.button("🚀 START/STOP CONTINUOUS TRADING", type="primary", use_container_width=True):
    st.session_state.continuous = not st.session_state.continuous
    state = "STARTED" if st.session_state.continuous else "STOPPED"
    add_log(f"Continuous trading {state}")

if col2.button("📊 Run One Cycle", use_container_width=True):
    execute_cycle()
    st.session_state.last_cycle_time = time.time()

if col3.button("🔄 Refresh Log", use_container_width=True):
    add_log("Log refreshed")


# -------------------------
# Continuous Mode
# -------------------------
if st.session_state.continuous:
    now = time.time()
    if now - st.session_state.last_cycle_time >= 10:
        execute_cycle()
        st.session_state.last_cycle_time = now

    st.experimental_rerun()


# -------------------------
# Log Output
# -------------------------
st.subheader("Live Debug Log")

for entry in reversed(st.session_state.log[-30:]):
    if "✅ ORDER SUBMITTED" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    elif "🛑" in entry:
        st.warning(entry)
    else:
        st.info(entry)
