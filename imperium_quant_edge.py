# ============================================================
#  IMPERIUM QUANT EDGE v7.3 — Adaptive RL Trading Platform
#  - RL core (state, reward, policy update)
#  - Meta-policy switching (Conservative / Aggressive / Predator)
#  - Cross-market learning
#  - Memory embeddings + pattern engine
#  - Self-tuning risk engine
#  - Hedging engine
#  - Portfolio-level RL (v7)
#  - Margin + withdrawable balance + leverage (v7.1)
#  - IBKR-synced balance & withdrawable funds (safe, non-blocking)
#  - Non-blocking continuous mode (no while loops in UI path)
#  - Real IBKR integration (FX + XAU + BTC)
#  - Streamlit UI
# ============================================================

import streamlit as st
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque
from collections import deque
from datetime import datetime, timezone

from ib_async import IB, Forex, MarketOrder, Contract, Crypto, Commodity

# ============================================================
#  RL CONFIGURATION
# ============================================================

@dataclass
class RLConfig:
    gamma: float = 0.92
    base_lr: float = 0.25
    min_lr: float = 0.05
    max_lr: float = 0.60
    meta_strength: float = 0.15
    pattern_weight: float = 0.35
    memory_weight: float = 0.25
    reward_vol_boost: float = 1.4
    reward_trend_boost: float = 1.2
    max_memory: int = 20


@dataclass
class MarketMemory:
    states: Deque[List[float]] = field(default_factory=lambda: deque(maxlen=20))
    last_pattern_score: float = 0.0


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

    memory: MarketMemory = field(default_factory=MarketMemory)


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

    margin_used: float = 0.0
    free_margin: float = 100_000.0
    withdrawable_balance: float = 100_000.0


@dataclass
class EngineConfig:
    mode: str = "Hybrid"
    ai_aggressiveness: float = 1.0
    news_blackout: bool = True
    hedging_enabled: bool = True
    max_usd_exposure: int = 300_000

    rl: RLConfig = field(default_factory=RLConfig)

    meta_mode: str = "ADAPTIVE"

    max_leverage: float = 10.0
    min_leverage: float = 1.0
    current_leverage: float = 3.0


MARGIN_REQUIREMENTS = {
    "EURUSD": 0.02,
    "GBPUSD": 0.02,
    "USDJPY": 0.02,
    "USDCAD": 0.02,
    "XAUUSD": 0.05,
    "BTCUSD": 0.20,
}

# ============================================================
#  SESSION STATE
# ============================================================

if "ib" not in st.session_state:
    st.session_state.ib = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "log" not in st.session_state:
    st.session_state.log = []
if "continuous" not in st.session_state:
    st.session_state.continuous = False

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

# ============================================================
#  IBKR CONNECTION + ACCOUNT SYNC (SAFE)
# ============================================================

def build_contract(symbol: str) -> Contract:
    if symbol in ["EURUSD", "GBPUSD", "USDJPY", "USDCAD"]:
        return Forex(symbol)
    if symbol == "XAUUSD":
        c = Commodity()
        c.symbol = "XAU"
        c.exchange = "SMART"
        c.currency = "USD"
        return c
    if symbol == "BTCUSD":
        return Crypto("BTC", "USD")
    raise ValueError(f"Unsupported symbol: {symbol}")


def connect_ibkr():
    if st.session_state.connected:
        add_log("Already connected to IBKR.")
        return
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=1)
        st.session_state.ib = ib
        st.session_state.connected = True
        add_log("Connected to IBKR.")
    except Exception as e:
        add_log(f"IBKR connection failed: {e}")
        st.session_state.connected = False


def ensure_connection():
    if not st.session_state.connected or st.session_state.ib is None:
        connect_ibkr()
    return st.session_state.ib


def sync_account_from_ibkr():
    """Non-blocking-ish: only runs if already connected, fully wrapped in try/except."""
    ib = st.session_state.ib
    if ib is None or not st.session_state.connected:
        return
    acct = st.session_state.account
    try:
        summary = ib.accountSummary()
        net_liq = None
        avail_funds = None
        for row in summary:
            if row.tag == "NetLiquidation":
                net_liq = float(row.value)
            if row.tag in ("AvailableFunds", "AvailableFunds-S"):
                avail_funds = float(row.value)
        if net_liq is not None:
            acct.balance = net_liq
            acct.last_equity = net_liq
            acct.peak_equity = max(acct.peak_equity, net_liq)
        if avail_funds is not None:
            acct.free_margin = avail_funds
            acct.withdrawable_balance = avail_funds
        add_log(f"IBKR sync: balance={acct.balance:.2f}, withdrawable={acct.withdrawable_balance:.2f}")
    except Exception as e:
        add_log(f"IBKR account sync failed: {e}")

# ============================================================
#  STATE ENGINE + FEATURES
# ============================================================

def compute_momentum(price: float, last_price: float) -> float:
    if last_price == 0:
        return 0.0
    return (price - last_price) / last_price


def update_regime(m: MarketState, price: float, last_price: float):
    mom = compute_momentum(price, last_price)
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


def pattern_score(m: MarketState) -> float:
    if len(m.memory.states) < 5:
        return 0.0
    *prev, last = list(m.memory.states)
    if not prev:
        return 0.0
    dim = len(last)
    means = [sum(s[i] for s in prev) / len(prev) for i in range(dim)]
    dist = sum((last[i] - means[i]) ** 2 for i in range(dim)) ** 0.5
    score = -dist * 3.0
    score = max(-1.0, min(1.0, score))
    m.memory.last_pattern_score = score
    return score


def push_memory_state(m: MarketState):
    sf = max(-2.0, min(2.0, m.score_fast)) / 2.0
    ss = max(-2.0, min(2.0, m.score_slow)) / 2.0
    sa = max(-2.0, min(2.0, m.alpha)) / 2.0
    sv = max(0.0, min(0.01, m.vol_ema)) / 0.01
    sm = max(-0.01, min(0.01, m.mom_ema)) / 0.01
    m.memory.states.append([sf, ss, sa, sv, sm])


def compute_factor_scores(symbol: str, price: float, last_price: float, aggressiveness: float):
    mom = compute_momentum(price, last_price)
    bias = {
        "EURUSD": 0.05,
        "GBPUSD": 0.03,
        "USDJPY": -0.02,
        "USDCAD": 0.00,
        "XAUUSD": 0.08,
        "BTCUSD": 0.15,
    }.get(symbol, 0.0)
    fast = mom * 5 + random.uniform(-0.5, 0.5) * aggressiveness + bias
    slow = bias + random.uniform(-0.2, 0.2) * (aggressiveness * 0.5)
    fast = max(-1.5, min(1.5, fast))
    slow = max(-1.0, min(1.0, slow))
    return fast, slow


def build_state_vector(m: MarketState) -> List[float]:
    regime_map = {
        "LOW_VOL": -1.0,
        "NORMAL": 0.0,
        "HIGH_VOL": 1.0,
        "UP_TREND": 0.8,
        "DOWN_TREND": -0.8,
    }
    regime_val = regime_map.get(m.regime, 0.0)
    if m.memory.states:
        mem_dim = len(m.memory.states[0])
        mem_mean = [
            sum(s[i] for s in m.memory.states) / len(m.memory.states)
            for i in range(mem_dim)
        ]
    else:
        mem_mean = [0.0] * 5
    return [
        m.score_fast,
        m.score_slow,
        m.alpha,
        m.vol_ema,
        m.mom_ema,
        m.memory.last_pattern_score,
        *mem_mean,
        m.position / 100000.0,
        m.unrealized_pnl / 1000.0,
        regime_val,
    ]

# ============================================================
#  RL CORE
# ============================================================

def shaped_reward(m: MarketState, raw_pnl: float, eng: EngineConfig) -> float:
    reward = raw_pnl
    if m.regime == "HIGH_VOL":
        reward *= eng.rl.reward_vol_boost
    if m.regime in ["UP_TREND", "DOWN_TREND"]:
        reward *= eng.rl.reward_trend_boost
    if raw_pnl < 0:
        reward *= 0.8
    acct = st.session_state.account
    if len(acct.equity_curve) > 20:
        rets = [
            (acct.equity_curve[i] - acct.equity_curve[i - 1]) / acct.equity_curve[i - 1]
            for i in range(1, len(acct.equity_curve))
        ]
        avg_r = sum(rets) / len(rets)
        var_r = sum((r - avg_r) ** 2 for r in rets) / len(rets)
        vol_r = var_r ** 0.5 if var_r > 0 else 0.0
        if vol_r > 0:
            sharpe_like = avg_r / vol_r
            reward *= (1.0 + 0.3 * max(-1.0, min(1.0, sharpe_like)))
    return reward


def rl_update(m: MarketState, reward: float, eng: EngineConfig):
    lr = eng.rl.base_lr
    scaled = max(-3.0, min(3.0, reward / 20.0))
    m.alpha_ema_pnl = (1 - lr) * m.alpha_ema_pnl + lr * scaled
    signal = max(-1.0, min(1.0, m.alpha_ema_pnl))
    m.alpha = (1 - lr) * m.alpha + lr * signal
    m.alpha = max(-2.0, min(2.0, m.alpha))
    m.trades_count += 1


def meta_update_learning_rate(acct: AccountState, eng: EngineConfig):
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    delta = equity - acct.last_equity
    acct.last_equity = equity
    slope = max(-1.0, min(1.0, delta / 200.0))
    eng.rl.base_lr += eng.rl.meta_strength * slope
    eng.rl.base_lr = max(eng.rl.min_lr, min(eng.rl.max_lr, eng.rl.base_lr))


def decay_alpha_all():
    eng = st.session_state.engine
    for m in st.session_state.markets.values():
        m.alpha *= eng.rl.gamma
        m.alpha_ema_pnl *= eng.rl.gamma


def score_to_action(score: float, threshold: float = 0.05) -> Optional[str]:
    if score > threshold:
        return "BUY"
    elif score < -threshold:
        return "SELL"
    else:
        return None


def combine_scores(m: MarketState, fast: float, slow: float, alpha: float, eng: EngineConfig):
    base = 0.6 * fast + 0.4 * slow
    pat = m.memory.last_pattern_score
    base += eng.rl.pattern_weight * pat
    if m.memory.states:
        mem_bias = sum(sum(s) for s in m.memory.states) / (len(m.memory.states) * 5.0)
        mem_bias = max(-1.0, min(1.0, mem_bias))
    else:
        mem_bias = 0.0
    base += eng.rl.memory_weight * mem_bias
    a = max(-2.0, min(2.0, alpha))
    if a > 0:
        return base * (1 + 1.2 * a)
    else:
        return base * (1 + 0.8 * a)


def apply_rl_reward(m: MarketState, trade_pnl: float, eng: EngineConfig):
    reward = shaped_reward(m, trade_pnl, eng)
    rl_update(m, reward, eng)

# ============================================================
#  META-POLICY
# ============================================================

def select_meta_mode(m: MarketState, acct: AccountState, eng: EngineConfig):
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    dd = 100 * (acct.peak_equity - equity) / acct.peak_equity
    if dd > acct.max_drawdown_pct * 0.5:
        return "CONSERVATIVE"
    if m.regime == "LOW_VOL":
        return "CONSERVATIVE"
    if m.regime in ["UP_TREND", "DOWN_TREND"]:
        return "AGGRESSIVE"
    if m.regime == "HIGH_VOL":
        return "PREDATOR"
    if m.alpha > 1.0:
        return "AGGRESSIVE"
    if m.alpha < -1.0:
        return "CONSERVATIVE"
    if m.alpha_ema_pnl > 0.5:
        return "AGGRESSIVE"
    if m.alpha_ema_pnl < -0.5:
        return "CONSERVATIVE"
    return "AGGRESSIVE"


def scale_risk_by_mode(base_risk: float, mode: str) -> float:
    if mode == "CONSERVATIVE":
        return base_risk * 0.7
    if mode == "AGGRESSIVE":
        return base_risk * 1.2
    if mode == "PREDATOR":
        return base_risk * 1.8
    return base_risk


def scale_lr_by_mode(lr: float, mode: str) -> float:
    if mode == "CONSERVATIVE":
        return lr * 0.8
    if mode == "AGGRESSIVE":
        return lr * 1.0
    if mode == "PREDATOR":
        return lr * 1.4
    return lr


def amplify_score_by_mode(score: float, mode: str) -> float:
    if mode == "CONSERVATIVE":
        return score * 1.0
    if mode == "AGGRESSIVE":
        return score * 1.2
    if mode == "PREDATOR":
        return score * 1.6
    return score


def apply_meta_policy(m: MarketState, acct: AccountState, eng: EngineConfig, raw_score: float):
    mode = select_meta_mode(m, acct, eng)
    eng.rl.base_lr = scale_lr_by_mode(eng.rl.base_lr, mode)
    adjusted_score = amplify_score_by_mode(raw_score, mode)
    scaled_risk = scale_risk_by_mode(acct.risk_pct, mode)
    eng.meta_mode = mode
    return mode, adjusted_score, scaled_risk

# ============================================================
#  EXECUTION + IBKR
# ============================================================

def qualify(symbol: str):
    ib = ensure_connection()
    if ib is None:
        add_log("IBKR not available for qualify().")
        return None
    contract = build_contract(symbol)
    try:
        ib.qualifyContracts(contract)
        return contract
    except Exception as e:
        add_log(f"Contract qualification failed for {symbol}: {e}")
        return None


def get_market_price(symbol: str) -> float:
    ib = ensure_connection()
    contract = build_contract(symbol)
    if ib is not None:
        try:
            ticker = ib.reqMktData(contract, "", False, False)
            ib.sleep(0.2)
            if ticker.last is not None:
                return ticker.last
            if ticker.close is not None:
                return ticker.close
            if ticker.marketPrice() is not None:
                return ticker.marketPrice()
        except Exception as e:
            add_log(f"Market data failed for {symbol}: {e}")
    m = st.session_state.markets[symbol]
    if m.last_price == 0:
        return random.uniform(1.0, 2.0)
    return m.last_price * (1 + random.uniform(-0.0005, 0.0005))


def place_order(symbol: str, action: str, size: int):
    ib = ensure_connection()
    if ib is None:
        add_log("IBKR not available for place_order().")
        return None
    contract = qualify(symbol)
    if contract is None:
        add_log(f"Order skipped — contract unavailable for {symbol}")
        return None
    order = MarketOrder(action, size)
    try:
        trade = ib.placeOrder(contract, order)
        add_log(f"Order sent: {symbol} {action} {size}")
        return trade
    except Exception as e:
        add_log(f"Order failed: {symbol} {action} {size} | {e}")
        return None


def process_fills(m: MarketState, acct: AccountState, trade):
    ib = st.session_state.ib
    if ib is None:
        return
    try:
        ib.sleep(0.5)
        for fill in trade.fills:
            price = fill.price
            qty = fill.execution.shares
            side = fill.execution.side
            if m.position != 0:
                pnl = (price - m.avg_price) * m.position
                acct.total_realized_pnl += pnl
                apply_rl_reward(m, pnl, st.session_state.engine)
            if side == "BOT":
                m.position += qty
            else:
                m.position -= qty
            m.avg_price = price
            m.trades_count += 1
            add_log(f"Fill: {m.symbol} {side} {qty} @ {price}")
    except Exception as e:
        add_log(f"Processing fills failed for {m.symbol}: {e}")


def hedge_if_needed(acct: AccountState):
    if not st.session_state.engine.hedging_enabled:
        return
    mkts = st.session_state.markets
    usd_exposure = sum(m.position for m in mkts.values())
    if abs(usd_exposure) < st.session_state.engine.max_usd_exposure:
        return
    hedge_size = -usd_exposure
    add_log(f"Hedging USD exposure: {hedge_size}")
    place_order("USDCAD", "BUY" if hedge_size > 0 else "SELL", abs(hedge_size))


def execute_action(m: MarketState, acct: AccountState, action: str, risk: float):
    add_log(f"EXECUTE_ACTION {m.symbol} action={action} risk={risk:.3f}")
    if action is None:
        return
    eng = st.session_state.engine
    base_notional = 10000 * risk
    notional = base_notional * eng.current_leverage
    size = int(max(1000, notional))
    trade = place_order(m.symbol, action, size)
    if trade:
        process_fills(m, acct, trade)
        hedge_if_needed(acct)

# ============================================================
#  PORTFOLIO RL + MARGIN + LEVERAGE + NETTING
# ============================================================

def update_margin(acct: AccountState, mkts: dict):
    total_margin = 0.0
    for symbol, m in mkts.items():
        if m.position == 0:
            continue
        margin_rate = MARGIN_REQUIREMENTS.get(symbol, 0.02)
        notional = abs(m.position * m.last_price)
        total_margin += notional * margin_rate
    acct.margin_used = total_margin
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    model_free = equity - acct.margin_used
    acct.free_margin = max(0.0, model_free)
    acct.withdrawable_balance = min(acct.withdrawable_balance, acct.free_margin)


def portfolio_rl_adjustment(acct: AccountState, eng: EngineConfig):
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    dd = (acct.peak_equity - equity) / acct.peak_equity
    if dd > 0.10:
        eng.ai_aggressiveness *= 0.9
    if acct.free_margin < equity * 0.2:
        eng.ai_aggressiveness *= 0.85
    if dd < 0.03 and acct.free_margin > equity * 0.5:
        eng.ai_aggressiveness *= 1.02
    eng.ai_aggressiveness = max(0.2, min(2.0, eng.ai_aggressiveness))


def update_leverage(acct: AccountState, eng: EngineConfig):
    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
    dd = (acct.peak_equity - equity) / acct.peak_equity
    if dd > 0.20:
        lev = 1.0
    elif dd > 0.10:
        lev = 2.0
    elif dd > 0.05:
        lev = 3.0
    else:
        lev = 5.0
    if len(acct.equity_curve) > 20:
        rets = [
            (acct.equity_curve[i] - acct.equity_curve[i - 1]) / acct.equity_curve[i - 1]
            for i in range(1, len(acct.equity_curve))
        ]
        avg_r = sum(rets) / len(rets)
        var_r = sum((r - avg_r) ** 2 for r in rets) / len(rets)
        vol_r = var_r ** 0.5 if var_r > 0 else 0.0
        if vol_r > 0:
            sharpe_like = avg_r / vol_r
            if sharpe_like > 1.0:
                lev *= 1.3
            elif sharpe_like < 0.0:
                lev *= 0.7
    lev = max(eng.min_leverage, min(eng.max_leverage, lev))
    eng.current_leverage = lev


def net_positions(mkts: dict):
    eur = mkts["EURUSD"].position
    gbp = mkts["GBPUSD"].position
    if eur * gbp <= 0:
        net = min(abs(eur), abs(gbp))
        mkts["EURUSD"].position -= net * (1 if eur > 0 else -1)
        mkts["GBPUSD"].position -= net * (1 if gbp > 0 else -1)
    xau = mkts["XAUUSD"].position
    btc = mkts["BTCUSD"].position
    if xau * btc < 0:
        hedge = min(abs(xau), abs(btc))
        mkts["XAUUSD"].position -= hedge * (1 if xau > 0 else -1)
        mkts["BTCUSD"].position -= hedge * (1 if btc > 0 else -1)

# ============================================================
#  TRADING CYCLE
# ============================================================

def run_trading_cycle():
    mkts = st.session_state.markets
    acct = st.session_state.account
    eng = st.session_state.engine

    # Safe IBKR sync (won't crash UI)
    try:
        sync_account_from_ibkr()
    except Exception as e:
        add_log(f"sync_account_from_ibkr() error: {e}")

    for symbol, m in mkts.items():
        if not m.enabled:
            continue

        price = get_market_price(symbol)
        last_price = m.last_price if m.last_price != 0 else price
        m.last_price = price
        m.last_update = datetime.now(timezone.utc)

        update_regime(m, price, last_price)

        fast, slow = compute_factor_scores(symbol, price, last_price, eng.ai_aggressiveness)
        m.score_fast = fast
        m.score_slow = slow

        push_memory_state(m)
        pattern_score(m)

        _ = build_state_vector(m)  # placeholder for future NN

        raw_score = combine_scores(m, fast, slow, m.alpha, eng)
        mode, adj_score, scaled_risk = apply_meta_policy(m, acct, eng, raw_score)
        action = score_to_action(adj_score)

        add_log(f"{symbol} raw={raw_score:.3f} adj={adj_score:.3f} action={action}")

        execute_action(m, acct, action, scaled_risk)

        if m.position != 0:
            m.unrealized_pnl = (price - m.avg_price) * m.position
        else:
            m.unrealized_pnl = 0.0

        acct.total_unrealized_pnl = sum(mm.unrealized_pnl for mm in mkts.values())
        equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl
        acct.equity_curve.append(equity)
        acct.peak_equity = max(acct.peak_equity, equity)

        meta_update_learning_rate(acct, eng)

        add_log(
            f"{symbol} | Mode={mode} | Score={adj_score:.3f} | "
            f"Pos={m.position} | PnL={m.unrealized_pnl:.2f}"
        )

    decay_alpha_all()
    update_margin(acct, mkts)
    portfolio_rl_adjustment(acct, eng)
    update_leverage(acct, eng)
    net_positions(mkts)

# ============================================================
#  CONTINUOUS MODE (NON-BLOCKING)
# ============================================================

def start_continuous():
    st.session_state.continuous = True
    add_log("Continuous mode enabled.")


def stop_continuous():
    st.session_state.continuous = False
    add_log("Continuous mode stopped.")

# ============================================================
#  UI
# ============================================================

def render_ui():
    st.set_page_config(page_title="Imperium Quant Edge v7.3", layout="wide")
    st.title("⚔️ Imperium Quant Edge v7.3 — Adaptive RL Trading Platform")

    acct = st.session_state.account
    mkts = st.session_state.markets
    eng = st.session_state.engine

    # Non-blocking continuous tick
    if st.session_state.continuous:
        run_trading_cycle()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Run One Cycle"):
            run_trading_cycle()

    with col2:
        if not st.session_state.continuous:
            if st.button("Start Continuous Mode"):
                start_continuous()
        else:
            if st.button("Stop Continuous Mode"):
                stop_continuous()

    with col3:
        if st.button("Connect / Reconnect IBKR"):
            connect_ibkr()

    with col4:
        if st.button("Manual IBKR Sync"):
            sync_account_from_ibkr()

    st.subheader("📊 Account Summary")

    equity = acct.balance + acct.total_realized_pnl + acct.total_unrealized_pnl

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Equity (IBKR NetLiq)", f"${equity:,.2f}")
        st.metric("Peak Equity", f"${acct.peak_equity:,.2f}")
    with c2:
        st.metric("Realized PnL", f"${acct.total_realized_pnl:,.2f}")
        st.metric("Unrealized PnL", f"${acct.total_unrealized_pnl:,.2f}")
    with c3:
        st.metric("Withdrawable Balance", f"${acct.withdrawable_balance:,.2f}")
        st.metric("Free Margin (model)", f"${acct.free_margin:,.2f}")
    with c4:
        st.metric("Margin Used (model)", f"${acct.margin_used:,.2f}")
        st.metric("Current Leverage", f"{eng.current_leverage:.2f}x")

    if acct.equity_curve:
        st.line_chart(acct.equity_curve)

    st.subheader("📈 Market States")

    for symbol, m in mkts.items():
        with st.expander(f"{symbol} — Regime: {m.regime}"):
            colA, colB, colC = st.columns(3)
            with colA:
                st.metric("Price", f"{m.last_price:.5f}")
                st.metric("Position", m.position)
                st.metric("Avg Price", f"{m.avg_price:.5f}")
            with colB:
                st.metric("Unrealized PnL", f"{m.unrealized_pnl:.2f}")
                st.metric("Alpha", f"{m.alpha:.3f}")
                st.metric("Pattern", f"{m.memory.last_pattern_score:.3f}")
            with colC:
                st.metric("Fast Score", f"{m.score_fast:.3f}")
                st.metric("Slow Score", f"{m.score_slow:.3f}")
                st.metric("Trades", m.trades_count)

    st.subheader("🧠 RL Diagnostics")
    st.write(f"Learning Rate: {eng.rl.base_lr:.4f}")
    st.write(f"Meta-Mode: {eng.meta_mode}")
    st.write(f"AI Aggressiveness: {eng.ai_aggressiveness}")
    st.write(f"Risk %: {acct.risk_pct}")

    st.subheader("📜 System Log")
    log_text = "\n".join(st.session_state.log[-200:])
    st.text_area("Logs", log_text, height=300)

# ============================================================
#  MAIN
# ============================================================

def main():
    render_ui()


if __name__ == "__main__":
    main()
