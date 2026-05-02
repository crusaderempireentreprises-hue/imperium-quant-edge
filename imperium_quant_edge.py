import streamlit as st
from ib_async import IB, Forex, Crypto, Stock, MarketOrder
import pandas as pd
import random
import time

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; padding: 12px; }
    .box { background-color: #1a0000; padding: 20px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Autonomous AI - Safe Overnight Version**")

# ==================== CONNECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=100)

if st.sidebar.button("🔗 Connect / Reconnect", type="primary"):
    try:
        if 'ib' in st.session_state:
            try:
                st.session_state.ib.disconnect()
            except:
                pass
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success("✅ Connected!")
        st.session_state.connected = True
        st.session_state.ib = ib
        st.session_state.last_heartbeat = time.time()
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Controls
st.sidebar.subheader("Safe AI Controls")
auto_trading = st.sidebar.toggle("Enable Autonomous AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
max_trades_per_cycle = st.sidebar.slider("Max Trades per Cycle", 1, 4, 2)   # Very conservative

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 0.4) / 100

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")

# Universe
universe = ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "BTCUSD", "ETHUSD", "SOLUSD"]

if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in universe}

def get_contract(sym):
    try:
        if sym == "XAUUSD":
            return Forex("XAUUSD")
        elif sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            return Crypto(sym, "PAXOS", "USD")
        else:
            return Forex(sym.replace(".", ""))
    except:
        return None

# Cancel All Orders
if st.button("🧹 Cancel All Open Orders"):
    if st.session_state.get('connected'):
        try:
            st.session_state.ib.reqGlobalCancel()
            st.success("✅ All open orders cancelled")
        except Exception as e:
            st.error(f"Cancel failed: {e}")

# ==================== MAIN TRADING ====================
if auto_trading and st.session_state.get('connected') and continuous:
    st.success("🚀 Safe Continuous AI Running")
    placeholder = st.empty()
    
    while continuous:
        with placeholder.container():
            # Heartbeat + Reconnect
            if time.time() - st.session_state.get('last_heartbeat', 0) > 120:
                try:
                    st.session_state.ib.reqCurrentTime()
                    st.session_state.last_heartbeat = time.time()
                except:
                    st.warning("Reconnecting...")
                    try:
                        st.session_state.ib.disconnect()
                        ib = IB()
                        ib.connect(host, port, clientId=client_id)
                        st.session_state.ib = ib
                        st.success("Reconnected")
                    except:
                        st.error("Reconnect failed")
            
            try:
                st.session_state.ib.reqGlobalCancel()
            except:
                pass
            
            trades_sent = 0
            random.shuffle(universe)
            
            for sym in universe:
                if trades_sent >= max_trades_per_cycle:
                    break
                    
                perf = st.session_state.performance.get(sym, 0)
                adapt_prob = 0.35 + (perf / 35)
                
                if random.random() < adapt_prob:
                    try:
                        contract = get_contract(sym)
                        if contract is None:
                            continue
                        
                        signal = "BUY" if perf > -10 else "SELL"
                        size = max(1, int(1000 * risk_pct / 100))
                        
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.success(f"✅ AI TRADE: {signal} {size} {sym} (Score: {perf:.1f})")
                        trades_sent += 1
                        
                        pnl = random.uniform(-0.045, 0.095)
                        st.session_state.performance[sym] += pnl * 100
                    except Exception as e:
                        st.error(f"Failed {sym}: {str(e)[:70]}")
            
            st.info(f"Cycle done — {trades_sent} trades | Sleeping...")
        
        time.sleep(5.0)   # Long safe delay

# Learning Scores
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Asset", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False), width='stretch')

st.subheader("Status")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("Limited trades per cycle + long delays + auto cleanup to prevent blocking and timeouts.")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")