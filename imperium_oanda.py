import os
# WebSocket stability tweak (prevents many Streamlit/Tornado WebSocketClosedError issues)
os.environ["STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION"] = "false"

import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional

import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary, AccountInstruments
from oandapyV20.endpoints.pricing import PricingInfo

# ============================================================
# USER CONFIG — INSERT YOUR CREDENTIALS HERE
# ============================================================

ACCOUNT_ID = "101-002-39303539-001"
ACCESS_TOKEN = "7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f"

# Core universe (always included)
BASE_SYMBOLS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CAD",
    "AUD_USD", "NZD_USD", "USD_CHF",
    "XAU_USD", "XAG_USD"
]

BASE_RISK_PCT = 0.5
MAX_TRADES_PER_HOUR = 20
MAX_DAILY_LOSS_PCT = 5.0
COOLDOWN_SECONDS = 30

# Dynamic universe config
DISCOVERY_REFRESH_SECONDS = 300   # how often to rescan markets
MAX_DYNAMIC_SYMBOLS = 8           # how many extra markets to add

# ============================================================
# STREAMLIT SETUP
# ============================================================

st.set_page_config(page_title="Imperium OANDA Hybrid AI v1.4.1", layout="wide")
st.title("⚔️ IMPERIUM OANDA HYBRID AI v1.4.1 — Dynamic Universe + WebSocket Safe")

st.markdown("""
<style>
.stApp { background-color: #0a0a0a; color: #ff3333; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class MarketState:
    symbol: str
    last: float = 0.0
    last_for_mom: float = 0.0
    mom_ema: float = 0.0
    vol_ema: float = 0.0
    atr: float = 0.0
    regime: str = "NEUTRAL"

    position: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    alpha: float = 0.0
    alpha_ema_pnl: float = 0.0

    last_trade_time: Optional[datetime] = None

# ============================================================
# SESSION STATE
# ============================================================

if "client" not in st.session_state:
    st.session_state.client = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "running" not in st.session_state:
    st.session_state.running = False
if "log" not in st.session_state:
    st.session_state.log = []
if "environment" not in st.session_state:
    st.session_state.environment = "practice"
if "history" not in st.session_state:
    st.session_state.history = []
if "pnl_curve" not in st.session_state:
    st.session_state.pnl_curve = []
if "trades_this_hour" not in st.session_state:
    st.session_state.trades_this_hour = 0
if "hour_start" not in st.session_state:
    st.session_state.hour_start = datetime.now(timezone.utc)
if "daily_nav_start" not in st.session_state:
    st.session_state.daily_nav_start = None
if "meta_mode" not in st.session_state:
    st.session_state.meta_mode = "AGGRESSIVE"
if "memory" not in st.session_state:
    st.session_state.memory = {s: {"wins": 0, "losses": 0} for s in BASE_SYMBOLS}
if "dynamic_universe" not in st.session_state:
    st.session_state.dynamic_universe = False
if "dynamic_symbols" not in st.session_state:
    st.session_state.dynamic_symbols: List[str] = []
if "last_discovery" not in st.session_state:
    st.session_state.last_discovery = datetime.now(timezone.utc) - timedelta(seconds=DISCOVERY_REFRESH_SECONDS)

if "markets" not in st.session_state:
    st.session_state.markets: Dict[str, MarketState] = {
        s: MarketState(symbol=s) for s in BASE_SYMBOLS
    }

def get_active_symbols() -> List[str]:
    base = list(BASE_SYMBOLS)
    dyn = list(st.session_state.dynamic_symbols) if st.session_state.dynamic_universe else []
    return sorted(list(dict.fromkeys(base + dyn)))

def ensure_market_states():
    active = get_active_symbols()
    for s in active:
        if s not in st.session_state.markets:
            st.session_state.markets[s] = MarketState(symbol=s)
            if s not in st.session_state.memory:
                st.session_state.memory[s] = {"wins": 0, "losses": 0}
    for s in list(st.session_state.markets.keys()):
        if s not in active:
            del st.session_state.markets[s]

# ============================================================
# LOGGING
# ============================================================

def add_log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    st.session_state.log.append(f"{ts} | {msg}")
    if len(st.session_state.log) > 300:
        st.session_state.log.pop(0)

# ============================================================
# OANDA CONNECTION
# ============================================================

def connect_oanda():
    try:
        client = oandapyV20.API(
            access_token=ACCESS_TOKEN,
            environment=st.session_state.environment
        )
        st.session_state.client = client
        st.session_state.connected = True
        add_log(f"Connected to OANDA ({st.session_state.environment})")
    except Exception as e:
        st.session_state.connected = False
        add_log(f"Connection failed: {e}")

def ensure_connection():
    if not st.session_state.connected or st.session_state.client is None:
        connect_oanda()

# ============================================================
# MARKET DISCOVERY ENGINE
# ============================================================

def discover_markets():
    if not st.session_state.dynamic_universe:
        return

    now = datetime.now(timezone.utc)
    if (now - st.session_state.last_discovery).total_seconds() < DISCOVERY_REFRESH_SECONDS:
        return

    st.session_state.last_discovery = now
    ensure_connection()
    if not st.session_state.connected:
        add_log("Discovery skipped: not connected.")
        return

    try:
        r = AccountInstruments(accountID=ACCOUNT_ID)
        resp = st.session_state.client.request(r)
        instruments = resp.get("instruments", [])
    except Exception as e:
        add_log(f"Discovery instruments error: {e}")
        return

    candidate_symbols = []
    for inst in instruments:
        name = inst.get("name")
        type_ = inst.get("type", "")
        if not name:
            continue
        if name in BASE_SYMBOLS:
            continue
        if type_ not in ("CURRENCY", "METAL"):
            continue
        candidate_symbols.append(name)

    if not candidate_symbols:
        add_log("Discovery: no candidate instruments found.")
        return

    spreads_info = []
    chunk_size = 25
    for i in range(0, len(candidate_symbols), chunk_size):
        chunk = candidate_symbols[i:i + chunk_size]
        instruments_str = ",".join(chunk)
        r = PricingInfo(accountID=ACCOUNT_ID, params={"instruments": instruments_str})
        try:
            resp = st.session_state.client.request(r)
            for p in resp.get("prices", []):
                sym = p["instrument"]
                bid = float(p["bids"][0]["price"])
                ask = float(p["asks"][0]["price"])
                mid = (bid + ask) / 2
                spread = ask - bid
                if mid <= 0:
                    continue
                spread_ratio = spread / mid
                spreads_info.append((sym, spread_ratio, mid))
        except Exception as e:
            add_log(f"Discovery pricing error: {e}")

    if not spreads_info:
        add_log("Discovery: no pricing info for candidates.")
        return

    filtered = [
        (sym, spread_ratio)
        for sym, spread_ratio, mid in spreads_info
        if spread_ratio < 0.0005
    ]

    if not filtered:
        add_log("Discovery: no tight-spread candidates.")
        return

    filtered.sort(key=lambda x: x[1])
    selected = [sym for sym, _ in filtered[:MAX_DYNAMIC_SYMBOLS]]

    st.session_state.dynamic_symbols = selected
    add_log(f"Discovery: dynamic symbols set to {selected}")
    ensure_market_states()

# ============================================================
# PRICE FETCHING
# ============================================================

def fetch_prices():
    if not st.session_state.connected:
        return

    ensure_market_states()
    symbols = get_active_symbols()
    if not symbols:
        return

    instruments = ",".join(symbols)
    r = PricingInfo(accountID=ACCOUNT_ID, params={"instruments": instruments})

    try:
        resp = st.session_state.client.request(r)
        for p in resp["prices"]:
            sym = p["instrument"]
            if sym not in st.session_state.markets:
                continue
            bid = float(p["bids"][0]["price"])
            ask = float(p["asks"][0]["price"])
            mid = (bid + ask) / 2
            m = st.session_state.markets[sym]
            prev = m.last if m.last > 0 else mid
            m.last = mid

            change = abs(mid - prev)
            m.atr = 0.9 * m.atr + 0.1 * change if m.atr > 0 else change
    except Exception as e:
        add_log(f"Pricing error: {e}")

# ============================================================
# ACCOUNT SUMMARY + RISK GUARDS
# ============================================================

def get_account_summary():
    if not st.session_state.connected:
        return None
    try:
        r = AccountSummary(accountID=ACCOUNT_ID)
        acc = st.session_state.client.request(r)["account"]
        nav = float(acc["NAV"])
        if st.session_state.daily_nav_start is None:
            st.session_state.daily_nav_start = nav
        st.session_state.pnl_curve.append(nav)
        return acc
    except Exception as e:
        add_log(f"AccountSummary error: {e}")
        return None

def check_daily_loss_guard(nav: float) -> bool:
    start = st.session_state.daily_nav_start
    if start is None:
        return False
    dd_pct = (start - nav) / start * 100.0
    if dd_pct >= MAX_DAILY_LOSS_PCT:
        add_log(f"DAILY LOSS LIMIT HIT ({dd_pct:.2f}%), stopping trading.")
        st.session_state.running = False
        return True
    return False

def reset_hour_if_needed():
    now = datetime.now(timezone.utc)
    if now - st.session_state.hour_start >= timedelta(hours=1):
        st.session_state.hour_start = now
        st.session_state.trades_this_hour = 0

# ============================================================
# INTELLIGENCE LAYER
# ============================================================

def compute_momentum(m: MarketState) -> float:
    if m.last_for_mom == 0:
        return 0.0
    return (m.last - m.last_for_mom) / m.last_for_mom

def update_regime(m: MarketState):
    mom = compute_momentum(m)
    vol = abs(mom)

    m.mom_ema = 0.9 * m.mom_ema + 0.1 * mom
    m.vol_ema = 0.9 * m.vol_ema + 0.1 * vol

    if m.vol_ema < 0.0003:
        m.regime = "LOW_VOL"
    elif m.vol_ema > 0.002:
        m.regime = "HIGH_VOL"
    else:
        m.regime = "NORMAL"

    if m.mom_ema > 0.0007:
        m.regime = "UP_TREND"
    elif m.mom_ema < -0.0007:
        m.regime = "DOWN_TREND"

def multi_tf_momentum(m: MarketState) -> float:
    mom1 = compute_momentum(m)
    mom5 = m.mom_ema
    return 0.7 * mom1 + 0.3 * mom5

def symbol_bias(symbol: str) -> float:
    if symbol.startswith("EUR_"): return 0.03
    if symbol.startswith("GBP_"): return 0.02
    if symbol.startswith("USD_JPY"): return -0.01
    if symbol.startswith("XAU_"): return 0.05
    return 0.0

def regime_intelligence(m: MarketState):
    if m.regime == "LOW_VOL":
        return {"risk_mult": 1.1, "signal_sensitivity": 0.8}
    if m.regime == "HIGH_VOL":
        return {"risk_mult": 0.6, "signal_sensitivity": 1.4}
    if m.regime == "UP_TREND":
        return {"bias": 0.25}
    if m.regime == "DOWN_TREND":
        return {"bias": -0.25}
    return {"risk_mult": 1.0, "signal_sensitivity": 1.0}

def adaptive_risk(nav: float, pnl_curve: List[float]) -> float:
    if len(pnl_curve) < 10:
        return 1.0
    recent = pnl_curve[-10:]
    slope = (recent[-1] - recent[0]) / abs(recent[0])
    if slope > 0.02:
        return 1.3
    if slope < -0.02:
        return 0.7
    return 1.0

def compute_score_components(m: MarketState, spread: float):
    mom = multi_tf_momentum(m)
    bias = symbol_bias(m.symbol)

    regime_score = 0.25 if m.regime == "UP_TREND" else -0.25 if m.regime == "DOWN_TREND" else 0.0

    vol_score = 0.2 if 0.0002 < m.vol_ema < 0.002 else -0.2 if m.vol_ema >= 0.002 else 0.0

    wins = st.session_state.memory.get(m.symbol, {"wins": 0})["wins"]
    losses = st.session_state.memory.get(m.symbol, {"losses": 0})["losses"]
    memory_score = (wins - losses) / max(1, wins + losses)

    momentum_score = mom * 60.0

    spread_penalty = -0.3 if spread > m.last * 0.0004 else 0.0

    return momentum_score, regime_score + bias, vol_score + spread_penalty, memory_score

def compute_final_score(m: MarketState, spread: float) -> float:
    momentum_score, regime_score, volatility_score, memory_score = compute_score_components(m, spread)

    ensemble = (
        0.40 * momentum_score +
        0.20 * regime_score +
        0.15 * volatility_score +
        0.10 * memory_score +
        0.15 * m.alpha
    ) / 5.0

    ri = regime_intelligence(m)
    ensemble *= ri.get("signal_sensitivity", 1.0)
    ensemble += ri.get("bias", 0.0)

    return max(-3.0, min(3.0, ensemble))

def score_to_action(score: float, threshold: float = 0.04):
    if score > threshold:
        return "BUY"
    if score < -threshold:
        return "SELL"
    return None

def decay_alpha_all():
    for m in st.session_state.markets.values():
        m.alpha *= 0.95
        m.alpha_ema_pnl *= 0.95

# ============================================================
# ORDER EXECUTION
# ============================================================

def compute_units(m: MarketState, nav: float) -> int:
    vol = m.vol_ema if m.vol_ema > 0 else 0.0005
    risk_factor = min(2.0, max(0.5, 0.5 / (vol + 1e-6)))
    equity_scale = min(2.0, max(0.5, nav / (st.session_state.daily_nav_start or nav)))
    regime_mult = 1.2 if m.regime == "LOW_VOL" else 0.8 if m.regime == "HIGH_VOL" else 1.0

    is_dynamic = m.symbol not in BASE_SYMBOLS
    dynamic_scale = 0.7 if is_dynamic else 1.0

    base_notional = nav * (BASE_RISK_PCT / 100.0)
    notional = base_notional * risk_factor * equity_scale * regime_mult * dynamic_scale
    if m.last <= 0:
        return 0
    return int(max(100, notional / m.last))

def place_order(m: MarketState, side: str, nav: float):
    now = datetime.now(timezone.utc)
    if m.last_trade_time and (now - m.last_trade_time).total_seconds() < COOLDOWN_SECONDS:
        add_log(f"Cooldown active for {m.symbol}, skipping.")
        return

    reset_hour_if_needed()
    if st.session_state.trades_this_hour >= MAX_TRADES_PER_HOUR:
        add_log("Max trades per hour reached, skipping.")
        return

    units = compute_units(m, nav)
    if units <= 0:
        add_log(f"Units <= 0 for {m.symbol}, skip.")
        return

    price = m.last
    pip = 0.0001
    if "JPY" in m.symbol:
        pip = 0.01
    if "XAU" in m.symbol or "XAG" in m.symbol:
        pip = 0.1

    atr_pips = max(10, m.atr / pip if m.atr > 0 else 20)
    sl_pips = atr_pips * 1.5
    tp_pips = atr_pips * 3.0

    sl_price = price - sl_pips * pip if side == "BUY" else price + sl_pips * pip
    tp_price = price + tp_pips * pip if side == "BUY" else price - tp_pips * pip

    data = {
        "order": {
            "units": str(units if side == "BUY" else -units),
            "instrument": m.symbol,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": f"{sl_price:.5f}"},
            "takeProfitOnFill": {"price": f"{tp_price:.5f}"}
        }
    }

    try:
        r = OrderCreate(ACCOUNT_ID, data=data)
        st.session_state.client.request(r)
        add_log(f"ORDER: {side} {units} {m.symbol} @ {price:.5f}")
        st.session_state.trades_this_hour += 1
        m.last_trade_time = now

        st.session_state.history.append({
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "symbol": m.symbol,
            "side": side,
            "units": units,
            "price": price,
            "sl": sl_price,
            "tp": tp_price
        })
    except Exception as e:
        add_log(f"ORDER FAILED {m.symbol}: {e}")

# ============================================================
# TRADING CYCLE
# ============================================================

def run_cycle():
    ensure_connection()
    if not st.session_state.connected:
        add_log("Not connected, skipping cycle.")
        return

    discover_markets()
    ensure_market_states()

    fetch_prices()
    acc = get_account_summary()
    if not acc:
        return

    nav = float(acc["NAV"])
    if check_daily_loss_guard(nav):
        return

    add_log("Cycle Start")

    for m in st.session_state.markets.values():
        if m.last == 0:
            continue

        if m.last_for_mom == 0:
            m.last_for_mom = m.last

        update_regime(m)

        spread_est = m.atr * 0.5 if m.atr > 0 else m.last * 0.0002

        quality = 0
        if abs(m.mom_ema) > 0.0004: quality += 1
        if 0.00015 < m.vol_ema < 0.003: quality += 1
        if spread_est < m.last * 0.0004: quality += 1
        if m.atr < m.last * 0.003: quality += 1

        score = compute_final_score(m, spread_est)

        add_log(f"{m.symbol} | Regime={m.regime} | Score={score:.3f} | Quality={quality}")

        if quality < 3:
            add_log(f"Low-quality setup on {m.symbol}, skipping.")
            continue

        action = score_to_action(score)

        if action:
            place_order(m, action, nav)

    decay_alpha_all()

# ============================================================
# UI — SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Settings")

    st.session_state.environment = st.selectbox(
        "Environment",
        ["practice", "live"],
        index=0
    )

    st.session_state.meta_mode = st.selectbox(
        "Meta Mode",
        ["CONSERVATIVE", "AGGRESSIVE", "PREDATOR"],
        index=1
    )

    st.session_state.dynamic_universe = st.checkbox(
        "Enable Dynamic Market Discovery",
        value=st.session_state.dynamic_universe
    )

    if st.button("Connect / Reconnect", use_container_width=True):
        connect_oanda()

    st.metric("Status", "Connected" if st.session_state.connected else "Disconnected")

    active_syms = ", ".join(get_active_symbols())
    st.caption(f"Active symbols: {active_syms}")

    if not st.session_state.running:
        if st.button("Start Continuous", use_container_width=True):
            st.session_state.running = True
            add_log("Continuous mode ON")
            st.rerun()
    else:
        if st.button("Stop Continuous", use_container_width=True):
            st.session_state.running = False
            add_log("Continuous mode OFF")
            st.rerun()

# ============================================================
# UI — MAIN
# ============================================================

col1, col2 = st.columns(2)

with col1:
    if st.button("Run One Cycle", use_container_width=True):
        run_cycle()

with col2:
    acc = get_account_summary()
    if acc:
        st.metric("Balance", acc["balance"])
        st.metric("NAV", acc["NAV"])
        st.metric("Unrealized PnL", acc["unrealizedPL"])
        if st.session_state.pnl_curve:
            st.line_chart(st.session_state.pnl_curve[-200:])

st.subheader("Trade History")
if st.session_state.history:
    st.table(st.session_state.history[-20:])

st.subheader("Log")
for entry in reversed(st.session_state.log[-100:]):
    st.text(entry)

# ============================================================
# CONTINUOUS MODE LOOP (WebSocket-safe)
# ============================================================

if st.session_state.running:
    try:
        run_cycle()
    except Exception as e:
        add_log(f"Cycle error: {e}")
    time.sleep(5)
    st.rerun()
