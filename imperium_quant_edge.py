def execute_cycle() -> None:
    if not st.session_state.connected or st.session_state.ib is None:
        add_log("Not connected – cycle skipped")
        return

    ib = st.session_state.ib

    add_log("--- Starting Trading Cycle ---")

    # Clean existing orders
    try:
        ib.reqGlobalCancel()
        add_log("Auto Global Cancel executed")
        ib.sleep(0.5)
    except Exception as e:
        add_log(f"❌ Global cancel failed: {e}")

    for sym in markets:
        try:
            add_log(f"→ Processing {sym}")

            # Build and qualify contract
            contract = get_contract(sym)
            add_log(f"Raw contract: {contract}")

            qualified = ib.qualifyContracts(contract)
            add_log(f"Qualified contracts: {qualified}")

            if not qualified:
                add_log(f"❌ Contract qualification failed for {sym}")
                continue

            contract = qualified[0]
            add_log(f"Using qualified contract: {contract}")

            # Order size (ensure minimum)
            size = max(25000, int(25000 * risk_pct))
            signal = random.choice(["BUY", "SELL"])

            add_log(f"Placing {signal} {size:,} {sym}")

            order = MarketOrder(signal, size)
            add_log(f"Order object: {order}")

            ib.placeOrder(contract, order)

            # Let IBKR process events
            ib.sleep(1.0)

            # Inspect trades / orders
            trades = ib.trades()
            orders = ib.orders()
            add_log(f"Trades after submit: {trades}")
            add_log(f"Open orders after submit: {orders}")

            add_log(f"✅ ORDER SUBMITTED (or attempted): {signal} {size:,} {sym}")

        except Exception as e:
            add_log(f"❌ ERROR on {sym}: {str(e)[:200]}")
