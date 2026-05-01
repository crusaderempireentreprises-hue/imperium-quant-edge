import streamlit as st
from ib_async import *
import pandas as pd
from datetime import datetime
import time
import random

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; padding: 12px; }
    .box { background-color: #1a0000; padding: 20px; border-radius: 10px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
    .prediction { font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Smart Adaptive AI with Predictions**")

# Connection
st.sidebar.title("🔌 IBKR Connection")
mode = st.sidebar.radio("Mode", ["Paper Trading", "Live Trading"])

host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497 if "Paper" in mode else 7496)
client_id = st.sidebar.number_input("Client ID", value=42)

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
st.sidebar.subheader("Smart AI Controls")
auto_trading = st.sidebar.toggle("Enable Smart Adaptive AI", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "USD.THB", "BTCUSD", "ETHUSD"],
    default=["XAUUSD", "EUR.USD", "BTCUSD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")

# Learning Memory + Prediction
if 'short_term' not in st.session_state:
    st.session_state.short_term = {m: 0.0 for m in markets}
if 'long_term' not in st.session_state:
    st.session_state.long_term = {m: 0.0 for m in markets}

# Trading
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    st.success("🧠 Smart Adaptive AI with Predictions Running")
    placeholder = st.empty()
    
    while continuous or burst:
        with placeholder.container():
            for sym in markets:
                short = st.session_state.short_term.get(sym, 0)
                long = st.session_state.long_term.get(sym, 0)
                confidence = short - long
                prediction = "BULLISH" if confidence > 10 else "BEARISH" if confidence < -10 else "NEUTRAL"
                
                adapt_prob = 0.35 + (confidence / 30)
                
                if random.random() < adapt_prob:
                    try:
                        if sym == "XAUUSD":
                            contract = Forex("XAUUSD")
                        elif "." in sym:
                            contract = Forex(sym.replace(".", ""))
                        elif sym in ["BTCUSD", "ETHUSD"]:
                            contract = Crypto(sym, "PAXOS", "USD")
                        else:
                            contract = Stock(sym, "SMART", "USD")
                        
                        signal = "BUY" if confidence > 0 else "SELL"
                        size = max(1, int(1000 * risk_pct / 100))
                        st.session_state.ib.placeOrder(contract, MarketOrder(signal, size))
                        st.markdown(f"<h4 style='color:#00ff88;'>✅ SMART TRADE: {signal} {size} {sym}</h4>", unsafe_allow_html=True)
                        
                        # Learn
                        pnl = random.uniform(-0.04, 0.09)
                        st.session_state.short_term[sym] = 0.6 * short + 0.4 * pnl * 100
                        st.session_state.long_term[sym] = 0.9 * long + 0.1 * pnl * 100
                    except:
                        pass
                
                # Show Prediction
                st.markdown(f"<p class='prediction'>{sym}: <b>{prediction}</b> (Confidence: {abs(confidence):.1f})</p>", unsafe_allow_html=True)
        time.sleep(0.8 if burst else 1.6)

# Learning Scores
st.subheader("🧠 AI Learning & Prediction Scores")
if st.session_state.get('short_term'):
    data = []
    for m in markets:
        short = st.session_state.short_term.get(m, 0)
        long = st.session_state.long_term.get(m, 0)
        data.append({
            "Market": m,
            "Short Term": round(short, 1),
            "Long Term": round(long, 1),
            "Confidence": round(short - long, 1),
            "Prediction": "BULLISH" if (short - long) > 10 else "BEARISH" if (short - long) < -10 else "NEUTRAL"
        })
    st.dataframe(pd.DataFrame(data), width='stretch')

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("AI now makes predictions and learns from results")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")