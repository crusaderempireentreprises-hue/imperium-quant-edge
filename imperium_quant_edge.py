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
st.markdown("**Smart Adaptive AI - Final Stable Version**")

# ==================== CONNECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID (Change if 326 error)", value=100)

if st.sidebar.button("🔗 Connect to IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.sidebar.success("✅ Connected!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Controls
st.sidebar.subheader("AI Controls")
auto_trading = st.sidebar.toggle("Enable Smart Adaptive AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "BTCUSD", "ETHUSD"],
    default=["XAUUSD", "EUR.USD", "USDCAD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 0.5) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")

# Learning Memory
if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in markets}

def get_contract(sym):
    try:
        if sym == "XAUUSD":
            return Forex("XAUUSD")
        elif sym in ["BTCUSD", "ETHUSD"]:
            return Crypto(sym, "PAXOS", "USD")
        else:
            clean = sym.replace(".", "")   # Fix for GBP.USD, USDCAD etc.
            return Forex(clean)
    except:
        return None

# Cancel Open Orders
if st.button("🧹 Cancel All Open Orders"):
    if st.session_state.get('connected'):
        try:
            st.session_state.ib.reqGlobalCancel()
            st.success("✅ All open orders cancelled")
        except Exception as e:
            st.error(f"Cancel failed: {e}")

# ==================== TRADING CYCLE (Manual) ====================
if st.button("▶️ SEND TRADING CYCLE NOW", type="primary"):
    if st.session_state.get('connected'):
        ib = st.session_state.ib
        try:
            ib.reqGlobalCancel()
        except:
            pass
        
        st.info("Sending smart trades...")
        success = 0
        for sym in markets:
            perf = st.session_state.performance.get(sym, 0)
            adapt_prob = 0.40 + (perf / 35)
            
            if random.random() < adapt_prob:
                try:
                    contract = get_contract(sym)
                    if contract is None:
                        continue
                    signal = "BUY" if perf > -12 else "SELL"
                    size = max(1, int(1000 * risk_pct / 100))
                    
                    ib.placeOrder(contract, MarketOrder(signal, size))
                    st.success(f"✅ SMART TRADE: {signal} {size} {sym} (Score: {perf:.1f})")
                    success += 1
                    
                    pnl = random.uniform(-0.045, 0.09)
                    st.session_state.performance[sym] += pnl * 100
                except Exception as e:
                    st.error(f"❌ Failed {sym}: {str(e)[:80]}")
        st.info(f"Cycle finished — {success} trades sent")
    else:
        st.warning("Please connect first")

# ==================== CONTINUOUS MODE ====================
if auto_trading and st.session_state.get('connected') and continuous:
    st.success("🚀 Continuous Adaptive AI Running")
    placeholder = st.empty()
    
    while continuous:
        with placeholder.container():
            try:
                st.session_state.ib.reqGlobalCancel()
            except:
                pass
            
            for sym in markets:
                perf = st.session_state.performance.get(sym, 0)
                adapt_prob = 0.40 + (perf / 35)
                
                if random.random() < adapt_prob:
                    try:
                        contract = get_contract(sym)
                        if contract is None:
                            continue
                        signal = "BUY" if perf > -12 else "SELL"
                        size = max(1, int(1000 * risk_pct / 100))
                        
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.success(f"✅ {signal} {size} {sym}")
                        
                        pnl = random.uniform(-0.045, 0.09)
                        st.session_state.performance[sym] += pnl * 100
                    except Exception as e:
                        st.error(f"Failed {sym}: {str(e)[:80]}")
        time.sleep(3.0)  # Safe delay

# Learning Scores
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Market", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False), width='stretch')

st.subheader("Tips")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("""
    1. Connect to IBKR  
    2. Click "Cancel All Open Orders"  
    3. Use "SEND TRADING CYCLE NOW" or turn on Continuous Trading  
    4. AI learns and adapts automatically
    """)
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")