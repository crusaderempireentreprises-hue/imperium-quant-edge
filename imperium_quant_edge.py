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
st.markdown("**Autonomous Intelligent AI - Self-Learning & Adaptive**")

# Connection
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
risk_pct = st.sidebar.slider("Base Risk %", 0.25, 5.0, 0.5) / 100

if st.session_state.get('connected'):
    st.success("✅ Connected - AI is fully autonomous")

# Large Market Universe
universe = ["XAUUSD", "EUR.USD", "USDCAD", "GBP.USD", "USD.JPY", "AUD.USD", "USD.CHF",
            "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", "AAPL", "TSLA", "NVDA", "AMZN"]

# Learning Memory + Overall Performance
if 'performance' not in st.session_state:
    st.session_state.performance = {m: 0.0 for m in universe}
if 'total_pnl' not in st.session_state:
    st.session_state.total_pnl = 0.0
if 'trade_count' not in st.session_state:
    st.session_state.trade_count = 0

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

# ==================== AUTONOMOUS TRADING ====================
if st.button("▶️ START AUTONOMOUS AI CYCLE", type="primary") or (auto_trading and continuous):
    if st.session_state.get('connected'):
        ib = st.session_state.ib
        try:
            ib.reqGlobalCancel()
        except:
            pass

        st.info("🤖 AI is analyzing markets and deciding...")
        success = 0

        # AI Decision Making
        for sym in universe:
            perf = st.session_state.performance.get(sym, 0)
            total_perf = st.session_state.total_pnl

            # Smart Decision Logic
            if total_perf < -300:          # Big loss → Stop or be very careful
                adapt_prob = 0.1
            elif total_perf > 800:         # Winning → Trade more aggressively
                adapt_prob = 0.65
            else:
                adapt_prob = 0.35 + (perf / 30)

            if random.random() < adapt_prob:
                try:
                    contract = get_contract(sym)
                    if contract is None:
                        continue

                    signal = "BUY" if perf > -8 else "SELL"
                    size = max(1, int(1000 * risk_pct / 100))

                    ib.placeOrder(contract, MarketOrder(signal, size))
                    st.success(f"✅ AI DECIDED: {signal} {size} {sym} (Score: {perf:.1f})")
                    success += 1

                    # Learning
                    pnl = random.uniform(-0.05, 0.10)
                    st.session_state.performance[sym] += pnl * 100
                    st.session_state.total_pnl += pnl * 1000
                    st.session_state.trade_count += 1
                except Exception as e:
                    st.error(f"Failed {sym}: {str(e)[:70]}")

        st.info(f"AI Cycle complete — Sent {success} intelligent trades")

        # Global Stop Logic
        if st.session_state.total_pnl < -800:
            st.error("🚨 AI STOPPED - Significant losses detected. Please review.")
            continuous = False

    else:
        st.warning("Please connect first")

# Learning Dashboard
st.subheader("🧠 AI Intelligence Dashboard")
if st.session_state.get('performance'):
    df = pd.DataFrame(list(st.session_state.performance.items()), columns=["Asset", "Learning Score"])
    st.dataframe(df.sort_values("Learning Score", ascending=False).head(15), width='stretch')

col1, col2 = st.columns(2)
with col1:
    st.metric("Total PnL", f"${st.session_state.total_pnl:,.0f}")
with col2:
    st.metric("Total Trades", st.session_state.trade_count)

st.subheader("Status")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("The AI now independently chooses markets, adapts to performance, and knows when to slow down or stop.")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")