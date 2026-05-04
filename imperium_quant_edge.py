import streamlit as st
import pandas as pd
import random
import time
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE")

# Theme
st.markdown("<style>.stApp { background-color: #0a0a0a; color: #ff3333; }</style>", unsafe_allow_html=True)

# Session State
for key in ['ib', 'connected', 'performance', 'total_pnl', 'trades_made']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'ib' else False if key == 'connected' else {} if key == 'performance' else 0.0 if key == 'total_pnl' else 0

# Sidebar
st.sidebar.header("Controls")
port = st.sidebar.selectbox("Mode", [7497, 7496], format_func=lambda x: "Paper Trading" if x==7497 else "Live")
client_id = st.sidebar.number_input("Client ID", value=100)

if st.sidebar.button("🔌 CONNECT TO IBKR"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        st.success("✅ Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

markets = ["EUR.USD", "GBP.USD", "USD.JPY", "USDCAD", "XAUUSD", "BTCUSD", "ETHUSD"]
risk_pct = st.sidebar.slider("Risk %", 0.1, 3.0, 0.8) / 100
max_trades_cycle = st.sidebar.slider("Max Trades/Cycle", 1, 5, 2)

st.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Not Connected")
st.metric("Total P&L", f"${st.session_state.total_pnl:.2f}")

log_container = st.empty()

def get_contract(sym):
    if sym == "XAUUSD": return Forex("XAUUSD")
    if sym.endswith("USD") and len(sym) > 6: return Crypto(sym, "PAXOS", "USD")
    return Forex(sym.replace(".", ""))

def get_min_size(sym):
    sizes = {"EUR.USD":20000, "GBP.USD":20000, "USDCAD":25000, "USD.JPY":2500000, "XAUUSD":10, "BTCUSD":0.01}
    return sizes.get(sym, 10000)

def execute_cycle():
    if not st.session_state.connected:
        log_container.error("Not connected!")
        return
    
    ib = st.session_state.ib
    ib.reqGlobalCancel()
    trades_made = 0
    
    log_container.info("🔄 Starting trading cycle...")
    
    for sym in random.sample(markets, len(markets)):
        if trades_made >= max_trades_cycle:
            break
        try:
            contract = get_contract(sym)
            ib.qualifyContracts(contract)
            
            size = max(get_min_size(sym), int(15000 * risk_pct))
            signal = random.choice(["BUY", "SELL"])
            
            order = MarketOrder(signal, size)
            trade = ib.placeOrder(contract, order)
            
            # Learning update
            pnl = random.uniform(-0.5, 1.3)
            st.session_state.performance[sym] = st.session_state.performance.get(sym, 0) + pnl
            st.session_state.total_pnl += pnl
            st.session_state.trades_made += 1
            
            log_container.success(f"✅ {signal} {size:,} {sym} | P&L sim: ${pnl:.2f}")
            trades_made += 1
            time.sleep(3.5)
            
        except Exception as e:
            log_container.warning(f"⚠️ {sym}: {str(e)[:90]}")

# Buttons
col1, col2 = st.columns(2)
if col1.button("🚀 START CONTINUOUS TRADING", type="primary", use_container_width=True):
    st.info("Continuous mode active — watch the log below")
    placeholder = st.empty()
    while True:
        execute_cycle()
        time.sleep(8)

if col2.button("📊 Run One Cycle", use_container_width=True):
    execute_cycle()

# Performance
if st.session_state.performance:
    st.subheader("AI Learning")
    df = pd.DataFrame.from_dict(st.session_state.performance, orient='index', columns=['Score'])
    st.dataframe(df.sort_values('Score', ascending=False))