import streamlit as st
from ib_async import *
import time

st.title("Imperium Quick Test")

if st.button("Connect & Place TEST Order"):
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=9999)   # Paper port
        st.success("Connected!")

        contract = Forex("EURUSD")
        ib.qualifyContracts(contract)
        
        order = MarketOrder("BUY", 25000)
        trade = ib.placeOrder(contract, order)
        
        st.success("✅ TEST ORDER SENT: BUY 25,000 EUR.USD")
        st.info("Check TWS Orders tab NOW!")
        
        time.sleep(5)
        ib.disconnect()
        
    except Exception as e:
        st.error(f"Error: {e}")

st.info("Make sure TWS Paper is open and running before clicking the button.")