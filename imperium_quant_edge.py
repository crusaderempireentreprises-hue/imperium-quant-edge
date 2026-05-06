import streamlit as st
from ib_async import *
import time

st.title("Imperium - Single Test Order")

st.write("Make sure TWS Paper is open on port 7497")

if st.button("🚀 SEND ONE TEST ORDER (EUR.USD)", type="primary", use_container_width=True):
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=9999)
        st.success("Connected!")

        contract = Forex("EURUSD")
        ib.qualifyContracts(contract)

        order = MarketOrder("BUY", 25000)   # Size that worked before
        trade = ib.placeOrder(contract, order)

        st.success("✅ TEST ORDER SENT: BUY 25,000 EUR.USD")
        st.info("Check TWS Orders tab immediately!")

        time.sleep(5)
        ib.disconnect()

    except Exception as e:
        st.error(f"Error: {str(e)}")

st.caption("Click the button above. Then look in TWS → Orders")