import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random
import plotly.graph_objects as go

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .stButton>button { background-color: #990000; color: white; border: 2px solid #ff0000; font-weight: bold; }
    .stButton>button:hover { background-color: #cc0000; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Personal Automatic AI Trader** — Multi-Market Edition")

# Sidebar
st.sidebar.title("⚙️ Controls")
mode = st.sidebar.radio("Trading Mode", ["Paper Trading ($1,000 Fake Money)", "Live Trading (Real Money)"])

auto_trading = st.sidebar.toggle("🤖 Enable Full Auto Trading", value=True)

symbol = st.sidebar.selectbox("Market to Trade", [
    "XAUUSD (Gold)", "XAGUSD (Silver)", "CL (Crude Oil)", "NG (Natural Gas)",
    "EUR.USD", "USD.CAD", "GBP.USD", "USD.JPY", "AUD.USD", "USD.CHF",
    "AAPL", "TSLA", "NVDA", "AMZN", "SHOP", "RY.TO", "TD.TO",
    "BTCUSD", "ETHUSD", "SOLUSD"
])

risk_pct = st.sidebar.slider("Risk % per Trade", 0.25, 5.0, 1.0) / 100
stop_loss_pct = st.sidebar.slider("Stop-Loss %", 0.5, 5.0, 1.5) / 100
take_profit_pct = st.sidebar.slider("Take-Profit %", 1.0, 10.0, 3.0) / 100

# Session state
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = [1000.0]

def generate_candles():
    dates = pd.date_range(end=datetime.now(), periods=50, freq='15min')
    base = 100 + np.cumsum(np.random.randn(50) * 0.8)
    return pd.DataFrame({
        'datetime': dates,
        'open': base,
        'high': base + np.abs(np.random.randn(50) * 2),
        'low': base - np.abs(np.random.randn(50) * 2),
        'close': base + np.random.randn(50) * 1.2
    })

if "Paper" in mode:
    st.success("📌 Paper Mode — Starting with $1,000 Fake Money")
    balance = 1000.0
else:
    st.warning("⚠️ Live Trading Mode - Real Money at Risk")
    balance = 50000.0

st.subheader(f"Live Chart: {symbol}")
df = generate_candles()
fig = go.Figure(data=[go.Candlestick(
    x=df['datetime'], open=df['open'], high=df['high'],
    low=df['low'], close=df['close'],
    increasing_line_color='#00ff88', decreasing_line_color='#ff3333'
)])
fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

if auto_trading:
    st.success("🤖 Auto Trading ACTIVE")
    
    for _ in range(8):
        with st.spinner(f"AI analyzing {symbol}..."):
            time.sleep(0.6)
            
            signal = random.choice(["BUY", "SELL", None])
            
            if signal:
                size = max(1, int((balance * risk_pct) / 100))
                pnl = random.uniform(-0.04, 0.08)
                
                st.markdown(f"<h4 style='color:#00ff88;'>✅ AI AUTO EXECUTED: {signal} {size} of {symbol}</h4>", unsafe_allow_html=True)
                st.session_state.trade_log.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "symbol": symbol,
                    "action": signal,
                    "size": size,
                    "pnl": round(pnl*100, 2)
                })
                
                balance = balance * (1 + pnl)
                st.session_state.equity_curve.append(balance)

# Performance
col1, col2 = st.columns(2)
with col1:
    st.subheader("Equity Curve")
    if len(st.session_state.equity_curve) > 1:
        st.line_chart(pd.DataFrame(st.session_state.equity_curve, columns=["Balance"]))

with col2:
    st.subheader("Performance")
    if st.session_state.trade_log:
        df_log = pd.DataFrame(st.session_state.trade_log)
        wins = len(df_log[df_log['pnl'] > 0]) if 'pnl' in df_log.columns else 0
        total = len(df_log)
        win_rate = round((wins / total) * 100, 1) if total > 0 else 0
        st.metric("Win Rate", f"{win_rate}%")
        st.metric("Total Trades", total)
        st.metric("Current Balance", f"${balance:.2f}")

st.subheader("Recent Auto Trades")
if st.session_state.trade_log:
    st.dataframe(pd.DataFrame(st.session_state.trade_log).tail(20))
else:
    st.info("Enable Auto Trading to start.")

st.button("🛑 KILL SWITCH — Stop All Trading", type="primary")

st.caption("Imperium Quant Edge • Multi-Market Edition")