import streamlit as st
from ib_async import *
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random

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
st.markdown("**Real Trading Signals (SMA + RSI)**")

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
        st.sidebar.success(f"✅ Connected to {mode}!")
        st.session_state.connected = True
        st.session_state.ib = ib
    except Exception as e:
        st.sidebar.error(f"❌ Failed: {e}")

# Controls
st.sidebar.subheader("Trading Controls")
auto_trading = st.sidebar.toggle("Enable Auto Trading", value=False)
continuous = st.sidebar.toggle("🔄 Continuous Trading (No Limit)", value=False)
burst = st.sidebar.toggle("⚡ Burst Mode", value=False)

markets = st.sidebar.multiselect("Select Markets", 
    ["XAUUSD", "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "USD.THB", "BTCUSD", "ETHUSD", "AAPL"],
    default=["XAUUSD", "EUR.USD", "BTCUSD"])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100

st.subheader("Active Markets")
st.write(", ".join(markets))

if st.session_state.get('connected'):
    st.success("✅ Connected to IBKR")
else:
    st.warning("Please connect first")

# ==================== REAL TRADING SIGNALS ====================
if auto_trading and st.session_state.get('connected') and (continuous or burst):
    ib = st.session_state.ib
    st.success(f"🚀 Real Signal Trading ACTIVE ({'Burst ⚡' if burst else 'Continuous'})")
    placeholder = st.empty()
    
    while continuous or burst:
        with placeholder.container():
            for sym in markets:
                try:
                    # Get real historical data
                    if sym == "XAUUSD":
                        contract = Forex("XAUUSD")
                    elif "." in sym:
                        contract = Forex(sym.replace(".", ""))
                    elif sym in ["BTCUSD", "ETHUSD"]:
                        contract = Crypto(sym, "PAXOS", "USD")
                    else:
                        contract = Stock(sym, "SMART", "USD")
                    
                    bars = ib.reqHistoricalData(
                        contract, endDateTime='', durationStr='1 D',
                        barSizeSetting='5 mins', whatToShow='MIDPOINT', useRTH=True
                    )
                    
                    df = util.df(bars)
                    if len(df) < 50:
                        continue
                    
                    # Real Signals: SMA Crossover + RSI
                    df['SMA12'] = df['close'].rolling(12).mean()
                    df['SMA26'] = df['close'].rolling(26).mean()
                    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    if last['SMA12'] > last['SMA26'] and prev['SMA12'] <= prev['SMA26'] and last['RSI'] < 70:
                        signal = "BUY"
                    elif last['SMA12'] < last['SMA26'] and prev['SMA12'] >= prev['SMA26'] and last['RSI'] > 30:
                        signal = "SELL"
                    else:
                        continue
                    
                    size = max(1, int(1000 * risk_pct / 100))
                    order = MarketOrder(signal, size)
                    ib.placeOrder(contract, order)
                    
                    st.markdown(f"<h4 style='color:#00ff88;'>✅ REAL SIGNAL: {signal} {size} {sym} @ ~{last['close']:.4f}</h4>", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Signal error on {sym}: {str(e)[:80]}")
        
        time.sleep(0.8 if burst else 2.0)

st.subheader("📜 Trade Log")
with st.container():
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.info("Check **TWS → Trades tab** for real executions")
    st.markdown('</div>', unsafe_allow_html=True)

st.button("🛑 KILL SWITCH", type="primary")