from ib_async import IB, Forex, MarketOrder

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=1)

contract = Forex("EURUSD")
ib.qualifyContracts(contract)

order = MarketOrder("BUY", 10000)
ib.placeOrder(contract, order)

ib.sleep(2)
print("Done")
