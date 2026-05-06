import streamlit as st
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ib_async import IB, Forex, MarketOrder

# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Imperium Quant Edge v4.1", layout="wide")
st.title("⚔️ IMPERIUM QUANT EDGE v4.1 — Adaptive + Meta AI (UTC‑Safe)")

st.markdown("""
<style>
.stApp { background-color: #050505; color: #ff3333; }
.block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------
@dataclass
class MarketState:
    symbol: str
    contract_symbol: str
    enabled: bool = True

    score_fast: float = 0.0
    score_slow: float = 0.0
    score_total: float = 0.0

    position: int = 0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    last_signal: Optional[str] = None
    last_price: float = 0.0
    last_update: Optional[datetime] = None

    alpha: float = 0.0
    alpha_ema_pnl: float = 0.0
    trades_count: int = 0

    regime: str = "NEUTRAL"
    vol_ema: float = 0.0
    mom_ema: float = 0.0


@dataclass
class AccountState:
    balance: float = 100_000.0
    risk_pct: float = 0.5
    max_drawdown_pct: float = 20.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trade_history: List[dict] = field(default_factory=list)
    peak_equity: float = 100_000.0
    last_equity: float = 100_000.0


@dataclass
class EngineConfig:
    mode: str = "Hybrid"
    ai_aggressiveness: float = 0.5
    news_blackout: bool = True
    hedging_enabled: bool = True
    max_usd_exposure: int = 300_000

    learning_rate: float = 0.35
    alpha_decay: float = 0.985
    ultra_aggressive: bool = False

    min_lr: float = 0.1
    max_lr: float = 0.6
    meta_strength: float = 0.15


# ---------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------
if "ib" not in st.session_state: st.session_state.ib = None
if "connected" not in st.session_state: st.session_state.connected = False
if "log" not in st.session_state: st.session_state.log = []
if "continuous" not in st.session_state: st.session_state.continuous = False
if "markets" not in st.session_state:
    st.session_state.markets: Dict[str, MarketState] = {
        "EURUSD": MarketState("EURUSD", "EURUSD"),
        "GBPUSD": MarketState("GBPUSD", "GBPUSD"),
        "USDJPY": MarketState("USDJPY", "USDJPY"),
        "USDCAD": MarketState("USDCAD", "USDCAD"),
        "XAUUSD": MarketState("XAUUSD", "XAUUSD"),
        "BTCUSD": MarketState("BTCUSD", "BTCUSD"),
    }
if "account" not in st.session_state:
    st.session_state.account = AccountState()
if "engine" not in st.session_state:
    st.session_state.engine = EngineConfig()


def add_log(msg: str):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    st.session_state.log.append(f"{ts} | {msg}")
    if len(st.session_state.log) > 400:
        st.session_state.log.pop(0)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("Connection")

port = st.sidebar.selectbox(
    "Mode",
    [7497, 7496],
    format_func=lambda x: "Paper (7497)" if x == 7497 else "Live (7496)"
)

client_id = st.sidebar.number_input("Client ID", value=9999, step=1)

if st.sidebar.button("🔌 CONNECT TO IBKR", type="primary"):
    try:
        ib = IB()
        ib.connect("127.0.0.1", port, clientId=client_id)

        def on_error(reqId, errorCode, errorString, contract):
            add_log(f"IB ERROR {errorCode}: {errorString}")

        ib.errorEvent += on_error

        st.session_state.ib = ib
        st.session_state.connected = True
        add_log("✅ Connected to IBKR")
        st.success("Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

if st.sidebar.button("🛑 CANCEL ALL OPEN ORDERS"):
    if st.session_state.connected:
        st.session_state.ib.reqGlobalCancel()
        add_log("🛑 Cancelled all orders")
        st.success("Cancelled!")

eng = st.session_state.engine
acct = st.session_state.account

st.sidebar.header("Engine Mode")
eng.mode = st.sidebar.selectbox("Engine mode", ["Simulated", "Live", "Hybrid"],
                                index=["Simulated", "Live", "Hybrid"].index(eng.mode))

st.sidebar.header("Risk & AI")
acct.risk_pct = st.sidebar.slider("Base risk % per trade", 0.1, 3.0, acct.risk_pct, 0.1)
acct.max_drawdown_pct = st.sidebar.slider("Max drawdown % (kill switch)", 5.0, 60.0, acct.max_drawdown_pct, 1.0)
eng.ai_aggressiveness = st.sidebar.slider("AI aggressiveness", 0.0, 1.0, eng.ai_aggressiveness, 0.05)
eng.hedging_enabled = st.sidebar.checkbox("Enable hedging", value=eng.hedging_enabled)
eng.news_blackout = st.sidebar.checkbox("News blackout mode", value=eng.news_blackout)
eng.learning_rate = st.sidebar.slider("Base learning rate (alpha)", 0.1, 0.6, eng.learning_rate, 0.05)
eng.alpha_decay = st.sidebar.slider("Alpha decay per cycle", 0.90, 0.999, eng.alpha_decay, 0.001)
eng.ultra_aggressive = st.sidebar.checkbox("ULTRA AGGRESSIVE AI", value=eng.ultra_aggressive)

st.sidebar.header("Markets")
for key, m in st.session_state.markets.items():
    m.enabled = st.sidebar.checkbox(m.symbol, value=m.enabled, key=f"mkt_{key}")

# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------
status_col, pnl_col, dd_col = st.columns(3)
status_col.metric("Status", "🟢 Connected" if st.session_state.connected else "🔴 Disconnected")

equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
acct.peak_equity = max(acct.peak_equity, equity)
drawdown = 0.0
if acct.peak_equity > 0:
    drawdown = 100.0 * (acct.peak_equity - equity) / acct.peak_equity

pnl_col.metric(
    "Account PnL",
    f"{acct.total_realized_pnl + acct.total_unrealized_pnl:,.2f}",
    f"Realized: {acct.total_realized_pnl:,.2f} | Unrealized: {acct.total_unrealized_pnl:,.2f}"
)
dd_col.metric("Drawdown %", f"{drawdown:.2f}%")

st.markdown("---")

# ---------------------------------------------------------
# NEWS BLACKOUT
# ---------------------------------------------------------
def in_news_blackout() -> bool:
    if not eng.news_blackout:
        return False
    now = datetime.now(timezone.utc)
    return now.minute in [58, 59, 0, 1, 2]


# ---------------------------------------------------------
# PRICE SOURCES
# ---------------------------------------------------------
def get_simulated_price(symbol: str, last_price: float) -> float:
    if last_price == 0:
        base = {
            "EURUSD": 1.08,
            "GBPUSD": 1.26,
            "USDJPY": 155.0,
            "USDCAD": 1.36,
            "XAUUSD": 2350.0,
            "BTCUSD": 65000.0,
        }.get(symbol, 1.0)
        last_price = base
    drift = random.uniform(-0.0015, 0.0015)
    return max(0.0001, last_price * (1 + drift))


def get_live_price(symbol: str, last_price: float) -> float:
    if not st.session_state.connected:
        return last_price or get_simulated_price(symbol, last_price)
    ib = st.session_state.ib
    try:
        contract = Forex(symbol)
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(0.5)
        price = ticker.last or ticker.close or ticker.marketPrice()
        if price and price > 0:
            return price
    except Exception as e:
        add_log(f"MKTDATA ERROR {symbol}: {e}")
    return last_price or get_simulated_price(symbol, last_price)


def get_price(symbol: str, last_price: float) -> float:
    if eng.mode == "Simulated":
        return get_simulated_price(symbol, last_price)
    elif eng.mode == "Live":
        return get_live_price(symbol, last_price)
    else:
        return get_live_price(symbol, last_price)


# ---------------------------------------------------------
# REGIME DETECTION
# ---------------------------------------------------------
def update_regime(m: MarketState, price: float, last_price: float):
    if last_price == 0:
        mom = 0.0
    else:
        mom = (price - last_price) / last_price

    vol = abs(mom)
    m.vol_ema = 0.9 * m.vol_ema + 0.1 * vol
    m.mom_ema = 0.9 * m.mom_ema + 0.1 * mom

    if m.vol_ema < 0.0005:
        m.regime = "LOW_VOL"
    elif m.vol_ema > 0.002:
        m.regime = "HIGH_VOL"
    else:
        m.regime = "NORMAL"

    if m.mom_ema > 0.0007:
        m.regime = "UP_TREND"
    elif m.mom_ema < -0.0007:
        m.regime = "DOWN_TREND"


# ---------------------------------------------------------
# AI MULTI-FACTOR + ADAPTIVE ALPHA
# ---------------------------------------------------------
def compute_factor_scores(symbol: str, price: float, last_price: float, aggressiveness: float):
    if last_price == 0:
        mom = 0.0
    else:
        mom = (price - last_price) / last_price

    bias = {
        "EURUSD": 0.05,
        "GBPUSD": 0.03,
        "USDJPY": -0.02,
        "USDCAD": 0.0,
        "XAUUSD": 0.08,
        "BTCUSD": 0.15,
    }.get(symbol, 0.0)

    fast = mom * 5 + random.uniform(-0.5, 0.5) * aggressiveness + bias
    slow = bias + random.uniform(-0.2, 0.2) * (aggressiveness * 0.5)

    fast = max(-1.5, min(1.5, fast))
    slow = max(-1.0, min(1.0, slow))
    return fast, slow


def cross_market_alpha(symbol: str) -> float:
    mkts = st.session_state.markets
    a = mkts[symbol].alpha
    if symbol == "GBPUSD" and "EURUSD" in mkts:
        a = 0.7 * a + 0.3 * mkts["EURUSD"].alpha
    if symbol == "USDCAD" and "USDJPY" in mkts:
        a = 0.7 * a + 0.3 * mkts["USDJPY"].alpha
    return a


def combine_scores(fast: float, slow: float, alpha: float) -> float:
    base = 0.6 * fast + 0.4 * slow
    a = max(-2.0, min(2.0, alpha))

    if eng.ultra_aggressive:
        if a > 0:
            return base * (1 + 2.0 * a)
        else:
            return base * (1 + 1.5 * a)

    if a > 0:
        return base * (1 + 1.2 * a)
    else:
        return base * (1 + 0.8 * a)


def score_to_signal(score: float, threshold: float = 0.2) -> Optional[str]:
    if score > threshold:
        return "BUY"
    elif score < -threshold:
        return "SELL"
    else:
        return None


# ---------------------------------------------------------
# META-LEARNING
# ---------------------------------------------------------
def meta_update_learning_rate():
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    delta = equity - acct.last_equity
    acct.last_equity = equity

    slope = max(-1.0, min(1.0, delta / 200.0))
    eng.learning_rate += eng.meta_strength * slope
    eng.learning_rate = max(eng.min_lr, min(eng.max_lr, eng.learning_rate))


# ---------------------------------------------------------
# RISK ENGINE
# ---------------------------------------------------------
def effective_risk_pct(m: MarketState) -> float:
    base = acct.risk_pct
    a = max(-2.0, min(2.0, m.alpha))

    if m.regime in ["UP_TREND", "DOWN_TREND"]:
        base *= 1.2
    elif m.regime == "HIGH_VOL":
        base *= 0.7
    elif m.regime == "LOW_VOL":
        base *= 0.9

    if a > 0:
        base *= (1 + 0.5 * a)
    else:
        base *= (1 + 0.7 * a)

    return max(0.05, min(5.0, base))


def calc_position_size(symbol: str, price: float, risk_pct: float, balance: float) -> int:
    risk_amount = balance * (risk_pct / 100.0)
    if price <= 0:
        return 0
    nominal_per_unit = price * 80
    size = int(risk_amount / nominal_per_unit)
    return max(1, size * 1000)


def portfolio_kill_switch() -> bool:
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    if acct.peak_equity <= 0:
        return False
    dd = 100.0 * (acct.peak_equity - equity) / acct.peak_equity
    if dd >= acct.max_drawdown_pct:
        add_log(f"⚠️ KILL SWITCH TRIGGERED: drawdown {dd:.2f}%")
        return True
    return False


# ---------------------------------------------------------
# PNL & POSITIONS
# ---------------------------------------------------------
def update_unrealized_pnl():
    total_unreal = 0.0
    for m in st.session_state.markets.values():
        if m.position != 0:
            m.last_price = get_price(m.symbol, m.last_price)
            if m.position > 0:
                m.unrealized_pnl = (m.last_price - m.avg_price) * abs(m.position) * 0.0001
            else:
                m.unrealized_pnl = (m.avg_price - m.last_price) * abs(m.position) * 0.0001
        else:
            m.unrealized_pnl = 0.0
            m.last_price = get_price(m.symbol, m.last_price)
        total_unreal += m.unrealized_pnl
    acct.total_unrealized_pnl = total_unreal


def update_alpha(market: MarketState, trade_pnl: float):
    lr = eng.learning_rate
    scaled = max(-3.0, min(3.0, trade_pnl / 20.0))
    market.alpha_ema_pnl = (1 - lr) * market.alpha_ema_pnl + lr * scaled
    signal = max(-1.0, min(1.0, market.alpha_ema_pnl))
    market.alpha = (1 - lr) * market.alpha + lr * signal
    market.alpha = max(-2.0, min(2.0, market.alpha))
    market.trades_count += 1


def decay_alpha_all():
    for m in st.session_state.markets.values():
        m.alpha *= eng.alpha_decay
        m.alpha_ema_pnl *= eng.alpha_decay


def apply_fill(market: MarketState, side: str, size: int, price: float):
    pos_before = market.position
    new_pos = pos_before + size if side == "BUY" else pos_before - size
    trade_pnl = 0.0

    if pos_before != 0 and (pos_before > 0 > new_pos or pos_before < 0 < new_pos):
        closed = min(abs(pos_before), abs(new_pos))
        direction = 1 if pos_before > 0 else -1
        pnl_per_unit = (price - market.avg_price) * direction * 0.0001
        trade_pnl = pnl_per_unit * closed
        market.realized_pnl += trade_pnl
        acct.total_realized_pnl += trade_pnl

    if