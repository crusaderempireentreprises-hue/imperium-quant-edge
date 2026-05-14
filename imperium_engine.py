import os
import sys
import time
import json
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

import oandapyV20
from oandapyV20.endpoints.accounts import AccountDetails, AccountInstruments
from oandapyV20.endpoints.pricing import PricingInfo
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.positions import PositionsDetails


# ============================================================
# Paths & logging
# ============================================================

HOME_DIR = os.path.expanduser("~")
DOWNLOADS_DIR = os.path.join(HOME_DIR, "Downloads")
LOG_DIR = os.path.join(DOWNLOADS_DIR, "imperium_logs")
os.makedirs(LOG_DIR, exist_ok=True)

ENGINE_LOG = os.path.join(LOG_DIR, "engine.log")
TRADES_FILE = os.path.join(LOG_DIR, "trades.jsonl")
STATE_FILE = os.path.join(LOG_DIR, "state.json")

logger = logging.getLogger("imperium_engine")
logger.setLevel(logging.INFO)
logger.handlers.clear()

fh = logging.FileHandler(ENGINE_LOG, encoding="utf-8")
fh.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(fmt)
ch.setFormatter(fmt)

logger.addHandler(fh)
logger.addHandler(ch)


# ============================================================
# Config: OANDA + environment
# ============================================================

IMPERIUM_ENV = os.getenv("IMPERIUM_ENV", "practice").lower().strip()
if IMPERIUM_ENV not in ("practice", "live"):
    IMPERIUM_ENV = "practice"

OANDA_API_KEY = os.getenv("7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f", "").strip()
OANDA_ACCOUNT_ID = os.getenv("101-002-39303539-001", "").strip()

OANDA_ENVIRONMENTS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

OANDA_API_URL = OANDA_ENVIRONMENTS[IMPERIUM_ENV]


# ============================================================
# Market discovery mode
# ============================================================

# conservative → majors + USD crosses + metals
# moderate     → FX + metals + indices
# full         → everything OANDA offers
DISCOVERY_MODE = os.getenv("IMPERIUM_DISCOVERY_MODE", "conservative").lower().strip()
if DISCOVERY_MODE not in ("conservative", "moderate", "full"):
    DISCOVERY_MODE = "conservative"


# ============================================================
# Base universe & parameters
# ============================================================

INSTRUMENTS = [
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "XAU_USD",
]

POLL_INTERVAL_SECONDS = 10
MAX_SPREAD_PIPS = 3.0
RISK_PER_TRADE = 0.005  # 0.5%


# ============================================================
# State handling
# ============================================================

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {
            "equity": None,
            "positions": {},
            "last_run": None,
            "meta_policy": "conservative",
            "baseline_equity": None,
            "instrument_stats": {},
            "blacklist": [],
        }
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        state = {}

    state.setdefault("equity", None)
    state.setdefault("positions", {})
    state.setdefault("last_run", None)
    state.setdefault("meta_policy", "conservative")
    state.setdefault("baseline_equity", None)
    state.setdefault("instrument_stats", {})
    state.setdefault("blacklist", [])
    return state


def save_state(state: Dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def append_trade_log(entry: Dict[str, Any]) -> None:
    try:
        with open(TRADES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to append trade log: {e}")


# ============================================================
# Instrument memory & blacklist
# ============================================================

def update_instrument_stats(
    state: Dict[str, Any],
    instrument: str,
    realized_pnl: float,
    win: Optional[bool]
) -> None:
    stats = state.setdefault("instrument_stats", {}).setdefault(instrument, {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "pnl": 0.0,
        "score": 0.0,
    })
    stats["trades"] += 1
    stats["pnl"] += realized_pnl
    if win is True:
        stats["wins"] += 1
    elif win is False:
        stats["losses"] += 1

    winrate = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0.0
    stats["score"] = stats["pnl"] + winrate * 10.0


def refresh_blacklist(state: Dict[str, Any]) -> None:
    stats = state.get("instrument_stats", {})
    blacklist = set(state.get("blacklist", []))

    for inst, s in stats.items():
        trades = s.get("trades", 0)
        score = s.get("score", 0.0)
        if trades >= 10 and score < -5.0:
            blacklist.add(inst)

    state["blacklist"] = sorted(list(blacklist))


# ============================================================
# OANDA helpers
# ============================================================

def get_oanda_client() -> Optional[oandapyV20.API]:
    if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
        logger.error("OANDA_API_KEY or OANDA_ACCOUNT_ID not set in environment.")
        return None
    try:
        client = oandapyV20.API(
            access_token=OANDA_API_KEY,
            environment="practice" if IMPERIUM_ENV == "practice" else "live"
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create OANDA client: {e}")
        return None


def fetch_account_equity(client: oandapyV20.API) -> Optional[float]:
    try:
        r = AccountDetails(accountID=OANDA_ACCOUNT_ID)
        client.request(r)
        acc = r.response.get("account", {})
        balance = float(acc.get("balance", 0.0))
        return balance
    except Exception as e:
        logger.error(f"Failed to fetch account equity: {e}")
        return None


def fetch_positions(client: oandapyV20.API) -> Dict[str, Any]:
    try:
        r = PositionsDetails(accountID=OANDA_ACCOUNT_ID)
        client.request(r)
        positions = {}
        for p in r.response.get("positions", []):
            instrument = p.get("instrument")
            long_units = float(p.get("long", {}).get("units", 0.0))
            short_units = float(p.get("short", {}).get("units", 0.0))
            positions[instrument] = {
                "long_units": long_units,
                "short_units": short_units,
            }
        return positions
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return {}


def fetch_prices(client: oandapyV20.API, instruments: List[str]) -> Dict[str, Dict[str, float]]:
    prices = {}
    if not instruments:
        return prices
    try:
        r = PricingInfo(accountID=OANDA_ACCOUNT_ID, params={"instruments": ",".join(instruments)})
        client.request(r)
        for p in r.response.get("prices", []):
            inst = p.get("instrument")
            bids = p.get("bids", [])
            asks = p.get("asks", [])
            if not bids or not asks:
                continue
            bid = float(bids[0]["price"])
            ask = float(asks[0]["price"])
            prices[inst] = {"bid": bid, "ask": ask}
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
    return prices


def place_market_order(
    client: oandapyV20.API,
    instrument: str,
    units: int,
    tag: str = "imperium"
) -> Optional[Dict[str, Any]]:
    try:
        data = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "clientExtensions": {
                    "tag": tag
                }
            }
        }
        r = OrderCreate(accountID=OANDA_ACCOUNT_ID, data=data)
        client.request(r)
        return r.response
    except Exception as e:
        logger.error(f"Failed to place order for {instrument}: {e}")
        return None


def fetch_all_instruments(client: oandapyV20.API) -> list:
    try:
        r = AccountInstruments(accountID=OANDA_ACCOUNT_ID)
        client.request(r)
        return r.response.get("instruments", [])
    except Exception as e:
        logger.error(f"Failed to fetch instruments: {e}")
        return []


def filter_instruments(raw: list) -> list:
    out = []

    for inst in raw:
        name = inst.get("name", "")
        type_ = inst.get("type", "")
        margin = float(inst.get("marginRate", 0.0))

        if DISCOVERY_MODE == "conservative":
            if not (
                name.endswith("_USD")
                or name.startswith("USD_")
                or name in ("XAU_USD", "XAG_USD")
            ):
                continue
        elif DISCOVERY_MODE == "moderate":
            if type_ not in ("CURRENCY", "METAL", "INDEX"):
                continue
        elif DISCOVERY_MODE == "full":
            pass

        if margin > 0.1 and DISCOVERY_MODE != "full":
            continue

        out.append(name)

    return out


# ============================================================
# Meta-policy & signal logic
# ============================================================

def choose_meta_policy(state: Dict[str, Any]) -> str:
    equity = state.get("equity")
    baseline = state.get("baseline_equity")

    if equity is None or baseline is None:
        return "conservative"

    change = (equity - baseline) / baseline

    if change <= -0.10:
        return "conservative"
    if change <= -0.03:
        return "neutral"

    if change >= 0.15:
        return "ultra"
    if change >= 0.05:
        return "aggressive"

    return "conservative"


def generate_signal(
    instrument: str,
    price: Dict[str, float],
    meta_policy: str,
    state: Dict[str, Any]
) -> str:
    stats = state.get("instrument_stats", {}).get(instrument, None)
    equity = state.get("equity") or 0.0

    if equity <= 0:
        return "hold"

    if meta_policy == "aggressive":
        explore_prob = 0.3
    elif meta_policy == "ultra":
        explore_prob = 0.5
    elif meta_policy == "conservative":
        explore_prob = 0.05
    else:
        explore_prob = 0.15

    if stats is None:
        return random.choice(["hold", "buy", "sell"]) if random.random() < explore_prob else "hold"

    score = stats.get("score", 0.0)

    if score > 5.0:
        bias = random.random()
        if bias < 0.45:
            return "buy"
        elif bias < 0.9:
            return "sell"
        else:
            return "hold"

    if score < -2.0:
        return "hold"

    if random.random() < explore_prob:
        return random.choice(["buy", "sell"])
    return "hold"


def compute_order_size(
    equity: float,
    instrument: str,
    price: Dict[str, float],
    meta_policy: str
) -> int:
    if equity <= 0:
        return 0

    risk_fraction = RISK_PER_TRADE
    if meta_policy == "aggressive":
        risk_fraction *= 2.0
    elif meta_policy == "ultra":
        risk_fraction *= 3.0

    risk_amount = equity * risk_fraction
    mid = (price["bid"] + price["ask"]) / 2.0
    if mid <= 0:
        return 0

    units = int(risk_amount / (mid * 100.0) * 1000)
    return max(units, 0)


# ============================================================
# Main engine loop
# ============================================================

def engine_loop():
    logger.info("Imperium Engine v3.5 starting...")
    logger.info(f"OANDA environment: {IMPERIUM_ENV}")
    logger.info(f"Discovery mode: {DISCOVERY_MODE}")
    logger.info(f"Log directory: {LOG_DIR}")

    state = load_state()
    client = get_oanda_client()
    if client is None:
        logger.error("No OANDA client. Engine will idle.")

    if client is not None:
        eq = fetch_account_equity(client)
        if eq is not None:
            if state.get("baseline_equity") is None:
                state["baseline_equity"] = eq
            state["equity"] = eq
            save_state(state)
            logger.info(f"Initial equity: {eq}")

    dynamic_instruments: List[str] = INSTRUMENTS[:]

    while True:
        loop_start = datetime.utcnow().isoformat()
        try:
            if client is None:
                client = get_oanda_client()
                if client is None:
                    logger.error("Still no OANDA client. Sleeping...")
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

            equity = fetch_account_equity(client)
            if equity is not None:
                state["equity"] = equity
                if state.get("baseline_equity") is None:
                    state["baseline_equity"] = equity

            positions = fetch_positions(client)
            state["positions"] = positions

            meta_policy = choose_meta_policy(state)
            state["meta_policy"] = meta_policy

            refresh_blacklist(state)

            raw_instruments = fetch_all_instruments(client)
            discovered = filter_instruments(raw_instruments)
            if discovered:
                dynamic_instruments = sorted(set(INSTRUMENTS + discovered))
            else:
                dynamic_instruments = INSTRUMENTS[:]

            prices = fetch_prices(client, dynamic_instruments)

            for inst in dynamic_instruments:
                if inst in state.get("blacklist", []):
                    continue

                p = prices.get(inst)
                if not p:
                    continue

                bid = p["bid"]
                ask = p["ask"]
                spread = (ask - bid) * 10000.0

                if spread > MAX_SPREAD_PIPS:
                    continue

                signal = generate_signal(inst, p, meta_policy, state)
                if signal == "hold":
                    continue

                if equity is None:
                    continue

                units = compute_order_size(equity, inst, p, meta_policy)
                if units <= 0:
                    continue

                if signal == "sell":
                    units = -units

                logger.info(f"Signal: {signal} {inst} units={units} meta={meta_policy}")

                resp = place_market_order(client, inst, units, tag=f"imperium-{meta_policy}")

                trade_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "instrument": inst,
                    "signal": signal,
                    "units": units,
                    "meta_policy": meta_policy,
                    "price": p,
                    "response": resp,
                }
                append_trade_log(trade_entry)

                # Placeholder: when you wire realized PnL, call update_instrument_stats here
                # update_instrument_stats(state, inst, realized_pnl, win)

            state["last_run"] = loop_start
            save_state(state)

        except Exception as e:
            logger.error(f"Engine loop error: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        engine_loop()
    except KeyboardInterrupt:
        logger.info("Imperium Engine stopped by KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"Fatal error in Imperium Engine: {e}", exc_info=True)
