import streamlit as st
import random
import time
from ib_async import IB, Forex, MarketOrder

# -------------------------
# Page Setup
# -------------------------
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
if "ib" not in st.session_state:
    st.session_state.ib = None

if "connected" not in st.session_state:
    st.session_state.connected = False

if "log" not in st.session_state:
    st.session_state.log = []

if "continuous" not in st.session_state:
    st.session_state.continuous = False

if "last_cycle_time" not in st.session_state:
    st.session_state.last_cycle_time = 0.0


def add_log(msg: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.log.append(f"{timestamp} | {msg}")
    if len(st.session_state.log) > 200:
        st.session_state.log.pop(0)


# -------------------------
# IBKR Error Callback
# -------------------------
def on_error(req_id, error_code, error_string, contract):
    add_log(f"IBKR ERROR {error_code} (reqId {req_id}): {error_string}")


# -------------------------
# Sidebar Controls
# -------------------------
st.sidebar.header("Controls")

port = st.sidebar.selectbox(
    "Mode",
    [7497, 7496],
    format_func=lambda x: "Paper Trading (7497)" if x == 7497 else "Live Trading (7496)",
)

# Random default client ID to avoid "already in use"
client_id = int(
    st.sidebar.number_input(
        "Client ID",
        value=random.randint(1000, 9999),
        step=1,
    )
)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect("127.0.0.1", port, clientId=client_id)

        # Attach error callback
        try:
            ib.errorEvent += on_error  # ib_async style
        except Exception:
            pass

        st.session_state.ib = ib
        st.session_state.connected = True

        add_log(f"✅ Connected to IBKR (clientId={client_id}, port={port})")
        st.success("Connected to IBKR!")

    except Exception as e:
        st.session_state.connected = False
        st.session_state.ib = None
        add_log(f"❌ Connection failed: {e}")
        st.error(f"Connection failed: {e}")


# -------------------------
# Cancel Orders
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

risk_pct = st.sidebar.slider(
    "Risk % per Trade",
    min_value=0.5,
    max_value=5.0,
    value=2.0,
) / 100.0

st.metric(
    "Status",
    "🟢 Connected" if st.session_state.connected else "🔴 Disconnected",
)


# -------------------------
# Contract Builder
# -------------------------
def get_contract(sym: str):
    if sym == "XAUUSD":
        return Forex("XAUUSD")
    return Forex(sym.replace(".", ""))


# -------------------------
# Trading Cycle
# -------------------------
def execute_cycle() -> None:
    if not st.session_state.connected or st.session_state.ib is None:
        add_log("Not connected – cycle skipped")
        return

    ib = st.session_state.ib

    add_log("--- Starting Trading Cycle ---")

    # Clean existing orders
    try:
        ib.reqGlobalCancel()
        add_log("Auto Global Cancel executed")
        ib.sleep(0.5)
    except Exception as e:
        add_log(f"❌ Global cancel failed: {e}")

    for sym in markets:
        try:
            add_log(f"→ Processing {sym}")

            # Build and qualify contract
            contract = get_contract(sym)
            qualified = ib.qualifyContracts(contract)

            if not qualified:
                add_log(f"❌ Contract qualification failed for {sym}")
                continue

            contract = qualified[0]

            # Order size (ensure minimum)
            size = max(25000, int(25000 * risk_pct))
            signal = random.choice(["BUY", "SELL"])

            add_log(f"Placing {signal} {size:,} {sym}")

            order = MarketOrder(signal, size)
            ib.placeOrder(contract, order)

            # Let IBKR process events
            ib.sleep(0.5)

            add_log(f"✅ ORDER SUBMITTED: {signal} {size:,} {sym}")

        except Exception as e:
            add_log(f"❌ ERROR on {sym}: {str(e)[:150]}")


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
# Continuous Mode (non-blocking)
# -------------------------
if st.session_state.continuous:
    now = time.time()
    if now - st.session_state.last_cycle_time >= 10:
        execute_cycle()
        st.session_state.last_cycle_time = now

    # Trigger rerun to keep continuous mode alive
    st.rerun()


# -------------------------
# Log Output
# -------------------------
st.subheader("Live Debug Log")

for entry in reversed(st.session_state.log[-40:]):
    if "✅ ORDER SUBMITTED" in entry:
        st.success(entry)
    elif "❌" in entry:
        st.error(entry)
    elif "🛑" in entry or "Global Cancel" in entry:
        st.warning(entry)
    else:
        st.info(entry)
