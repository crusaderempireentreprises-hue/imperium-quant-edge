from ib_async import IB, Forex, MarketOrder

ib = IB()
print("Connecting...")
ib.connect("127.0.0.1", 7497, clientId=1)

print("Qualifying contract...")
contract = Forex("EURUSD")
ib.qualifyContracts(contract)

print("Placing order...")
order = MarketOrder("BUY", 10000)
trade = ib.placeOrder(contract, order)

print("Sleeping for IBKR to process...")
ib.sleep(2)

print("Trades:", ib.trades())
print("Orders:", ib.orders())

ib.disconnect()
