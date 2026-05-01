import streamlit as st
from ib_async import *
import time
import random

st.set_page_config(page_title="Imperium Quant Edge - Test", layout="wide")

st.title("🩸 Imperium Quant Edge - Minimal Test")

st.sidebar.title("Connection")
host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497)
client_id = st.sidebar.number_input("Client ID", value=51)

if st.sidebar.button("🔗 Connect"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.session_state.ib = ib
        st.session_state.connected = True
        st.success("✅ Connected successfully!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

if st.session_state.get('connected'):
    st.success("Connected - Ready to test orders")
    
    if st.button("🚀 SEND 1 TEST TRADE (XAUUSD)", type="primary"):
        try:
            contract = Forex("XAUUSD")
            order = MarketOrder("BUY", 1)
            
            trade = st.session_state.ib.placeOrder(contract, order)
            st.success("✅ Order SENT to IBKR: BUY 1 XAUUSD")
            st.info("Check TWS → Trades tab immediately!")
        except Exception as e:
            st.error(f"Order failed: {e}")

    if st.button("🚀 SEND 1 TEST TRADE (USDCAD)"):
        try:
            contract = Forex("USDCAD")
            order = MarketOrder("BUY", 1)
            st.session_state.ib.placeOrder(contract, order)
            st.success("✅ Order SENT: BUY 1 USDCAD")
        except Exception as e:
            st.error(f"USDCAD failed: {e}")

st.info("After clicking the buttons, immediately check **TWS → Trades** and **Orders** tab.")