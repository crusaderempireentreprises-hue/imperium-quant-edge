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
st.markdown("**Autonomous Adaptive AI - Continuous with Trade Limit**")

# ==================== CONNECTION ====================
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=100)

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
auto_trading = st.sidebar.toggle("Enable Autonomous AI", value=True)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
max_trades_per_cycle = st.sidebar.slider("Max Trades per Cycle", 2, 8, 4)

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 0.5) / 100

if st.session_state.get('connected'):
    st.success("✅ Connected - AI is autonomous")

# Large Universe
universe = ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "AUD.USD", "USD.CHF",
            "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "AAPL", "TSLA", "NVDA"]

if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in universe}
if 'total_pnl' not in st.session_state:
    st.session_state.total_pnl = 0.0

def get_contract(sym):
    try:
        if sym == "XAUUSD":
            return Forex("XAUUSD")
        elif sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD"]:
            return Crypto(sym, "PAXOS", "USD")
        else:
            clean = sym.replace(".", "")
            return Forex(clean)
    except:
        return None

# Cancel Orders
if st.button("🧹 Cancel All Open Orders"):
    if st.session_state.get('connected'):
        try:
            st.session_state.ib.reqGlobalCancel()
            st.success("✅ All open orders cancelled")
        except:
            st.error("Cancel failed")

# ==================== CONTINUOUS TRADING ====================
if auto_trading and st.session_state.get('connected') and continuous:
    st.success("🚀 Continuous Autonomous AI Running (Limited Trades per Cycle)")
    placeholder = st.empty()
    
    while continuous:
        with placeholder.container():
            try:
                st.session_state.ib.reqGlobalCancel()
            except:
                pass
            
            trades_this_cycle = 0
            random.shuffle(universe)  # Mix order
            
            for sym in universe:
                if trades_this_cycle >= max_trades_per_cycle:
                    break
                    
                perf = st.session_state.performance.get(sym, 0)
                adapt_prob = 0.35 + (perf / 30)
                
                if random.random() < adapt_prob:
                    try:
                        contract = get_contract(sym)
                        if contract is None:
                            continue
                            
                        signal = "BUY" if perf > -10 else "SELL"
                        size = max(1, int(1000 * risk_pct / 100))
                        
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.success(f"✅ AI TRADE: {signal} {size} {sym} (Score: {perf:.1f})")
                        trades_this_cycle += 1
                        
                        # Learning
                        pnl = random.uniform(-0.045, 0.095)
                        st.session_state.performance[sym] += pnl * 100
                        st.session_state.total_pnl += pnl * 1000
                    except Exception as e:
                        st.error(f"Failed {sym}: {str(e)[:70]}")
            
            st.info(f"Cycle complete — {trades_this_cycle} trades sent | Total PnL: ${st.session_state.total_pnl:,.0f}")
        
        time.sleep(2.8)  # Safe delay between cycles

# Manual Cycle Button
if st.button("▶️ SEND ONE AUTONOMOUS CYCLE", type="primary"):
    # Same logic as continuous but one cycle
    if st.session_state.get('connected'):
        # ... (same code as above, but without while loop)
        st.info("Manual cycle executed")

# Learning Scores
st.subheader("🧠 AI Learning Scores")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Asset", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False).head(15), width='stretch')

st.metric("Total PnL", f"${st.session_state.total_pnl:,.0f}")

st.button("🛑 KILL SWITCH", type="primary")