import streamlit as st
from ib_async import *

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.title("🩸 Imperium Quant Edge")
st.markdown("**Real Balance Test**")

st.sidebar.title("Connection")
host = st.sidebar.text_input("Host", "127.0.0.1")
port = st.sidebar.number_input("Port", value=7497)
client_id = st.sidebar.number_input("Client ID", value=42)

if st.sidebar.button("🔗 Connect to IBKR"):
    try:
        ib = IB()
        ib.connect(host, port, clientId=client_id)
        st.success("✅ Connected successfully!")

        # Try to get balance
        summary = ib.accountSummary()
        for item in summary:
            if item.tag == "NetLiquidation":
                balance = float(item.value)
                st.markdown(f"**Real Balance: ${balance:,.2f}**", unsafe_allow_html=True)
                break
        else:
            st.warning("Connected but could not read balance")
    except Exception as e:
        st.error(f"Error: {e}")

st.info("Click Connect, then check if balance appears above.")