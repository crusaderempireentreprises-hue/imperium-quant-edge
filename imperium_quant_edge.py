import time
from ib_async import IB, Forex, MarketOrder

HOST = "127.0.0.1"
PORT = 7497          # 7497 = paper, 7496 = live
CLIENT_ID = 9999     # make sure this is NOT used anywhere else

def main():
    ib = IB()

    print(f"Connecting to IBKR at {HOST}:{PORT} with clientId={CLIENT_ID}...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID)

    # Simple error logger
    def on_error(req_id, error_code, error_string, contract):
        print(f"[IBKR ERROR] {error_code} (reqId {req_id}): {error_string}")

    try:
        ib.errorEvent += on_error
    except Exception:
        pass

    # Build EUR.USD contract
    contract = Forex("EURUSD")
    print("Qualifying contract EURUSD...")
    qualified = ib.qualifyContracts(contract)
    print("Qualified:", qualified)

    if not qualified:
        print("❌ Contract qualification failed. Exiting.")
        ib.disconnect()
        return

    contract = qualified[0]

    # Place a tiny market order
    size = 25000
    side = "BUY"
    print(f"Placing {side} {size} EURUSD...")

    order = MarketOrder(side, size)
    trade = ib.placeOrder(contract, order)

    # Let IBKR process events
    for i in range(10):
        ib.sleep(1)
        print(f"Tick {i+1} - trade status: {trade.orderStatus.status}")

    print("Final trade object:", trade)
    ib.disconnect()
    print("Disconnected.")

if __name__ == "__main__":
    main()
