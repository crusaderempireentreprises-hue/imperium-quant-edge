import streamlit as st
from ib_async import *
from datetime import datetime
import time

st.set_page_config(page_title="Imperium Quant Edge", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; color: #ffdddd; }
    h1, h2, h3 { color: #ff3333; }
    .box { background-color: #1a0000; padding: 25px; border-radius: 12px; border: 2px solid #ff3333; margin-bottom: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩸 Imperium Quant Edge")
st.markdown("**Balance Debug Version**")

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="box"><h3>🕒 Current Time</h3><h2 id="live-time"></h2></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="box"><h3>💰 Real IBKR Balance</h3><h2 id="balance-display">$ --.--</h2></div>', unsafe_allow_html=True)

st.markdown("""
<script>
function updateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('live-time').innerHTML = timeStr;
}
setInterval(updateTime, 1000);
updateTime();
</script>
""", unsafe_allow_html=True)

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
        st.success("Connection successful!")
    except Exception as e:
        st.sidebar.error(f"Connection Failed: {e}")

# Debug Refresh Balance
if st.sidebar.button("🔄 Debug Refresh Balance", type="primary"):
    if st.session_state.get('connected') and st.session_state.get('ib'):
        try:
            st.info("Fetching account summary...")
            summary = st.session_state.ib.accountSummary()
            st.write("Received", len(summary), "items from IBKR")
            
            balance_found = False
            for item in summary:
                st.write(f"Item: {item.tag} = {item.value}")
                if item.tag == "NetLiquidation":
                    balance = float(item.value)
                    st.session_state.balance = balance
                    st.markdown(f'<div class="box"><h2>💰 Real Balance: ${balance:,.2f}</h2></div>', unsafe_allow_html=True)
                    st.success("✅ Balance Found & Updated!")
                    balance_found = True
                    break
            
            if not balance_found:
                st.error("NetLiquidation not found in account summary")
        except Exception as e:
            st.error(f"Error during refresh: {e}")
    else:
        st.warning("Please connect first")

st.subheader("Status")
st.info("Click **Debug Refresh Balance** after connecting.")

st.button("🛑 KILL SWITCH", type="primary")