import os
import time
import json
import signal
import threading
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional

import oandapyV20
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.accounts import AccountSummary, AccountInstruments
from oandapyV20.endpoints.pricing import PricingInfo

# ============================================================
# USER CONFIG
# ============================================================

ACCOUNT_ID = "101-002-39303539-001"
ACCESS_TOKEN = "7426ebe2deca18e6267236ed8355063c-95cc837c9288005787ee86c50e167f2f"
ENVIRONMENT = "practice"  # "practice" or "live"

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
DISCOVERY_REFRESH_SECONDS = 300
MAX_DYNAMIC_SYMBOLS = 8

# Engine cycle interval (seconds)
CYCLE_INTERVAL_SECONDS = 5

# Logging folder
LOG_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "imperium_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "engine.log")
TRADES_FILE = os.path.join(LOG_DIR, "trades.jsonl")
STATE_FILE = os.path.join(LOG_DIR, "state.json")

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
# ENGINE STATE
# ============================================================

class ImperiumEngine:
    def __init__(self):
        self.client = None
        self.connected = False

        self.markets: Dict[str, MarketState] = {
            s: MarketState(symbol=s) for s in BASE_SYMBOLS
        }

        self.dynamic_universe = True
        self.dynamic_symbols: List[str] = []
        self.last_discovery = datetime.now(timezone.utc) - timedelta(seconds=DISCOVERY_REFRESH_SECONDS)

        self.memory = {s: {"wins": 0, "losses": 0} for s in BASE_SYMBOLS}

        self.trades_this_hour = 0
        self.hour_start = datetime.now(timezone.utc)
        self.daily_nav_start: Optional[float] = None
        self.pnl_curve: List[float] = []

        self.running = True
        self.lock = threading.Lock()

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    def log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {msg}"
        print(line)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def log_trade(self, trade: dict):
        try:
            with open(TRADES_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade) + "\n")
        except Exception:
            pass

    def save_state(self):
        try:
            state = {
                "dynamic_symbols": self.dynamic_symbols,
                "memory": self.memory,
                "pnl_curve": self.pnl_curve,
                "daily_nav_start": self.daily_nav_start,
                "trades_this_hour": self.trades_this_hour,
                "hour_start": self.hour_start.isoformat(),
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    # --------------------------------------------------------
    # CONNECTION
    # --------------------------------------------------------

    def connect_oanda(self):
        try:
            self.client = oandapyV20.API(
                access_token=ACCESS_TOKEN,
                environment=ENVIRONMENT
            )
            self.connected = True
            self.log(f"Connected to OANDA ({ENVIRONMENT})")
        except Exception as e:
            self.connected = False
            self.log(f"Connection failed: {e}")

    def ensure_connection(self):
        if not self.connected or self.client is None:
            self.connect_oanda()

    # --------------------------------------------------------
    # UNIVERSE MANAGEMENT
    # --------------------------------------------------------

    def get_active_symbols(self) -> List[str]:
        base = list(BASE_SYMBOLS)
        dyn = list(self.dynamic_symbols) if self.dynamic_universe else []
        return sorted(list(dict.fromkeys(base + dyn)))

    def ensure_market_states(self):
        active = self.get_active_symbols()
        for s in active:
            if s not in self.markets:
                self.markets[s] = MarketState(symbol=s)
                if s not in self.memory:
                    self.memory[s] = {"wins": 0, "losses": 0}
        for s in list(self.markets.keys()):
            if s not in active:
                del self.markets[s]

    def discover_markets(self):
        if not self.dynamic_universe:
            return

        now = datetime.now(timezone.utc)
        if (now - self.last_discovery).total_seconds() < DISCOVERY_REFRESH_SECONDS:
            return

        self.last_discovery = now
        self.ensure_connection()
        if not self.connected:
            self.log("Discovery skipped: not connected.")
            return

        try:
            r = AccountInstruments(accountID=ACCOUNT_ID)
            resp = self.client.request(r)
            instruments = resp.get("instruments", [])
        except Exception as e:
            self.log(f"Discovery instruments error: {e}")
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
            self.log("Discovery: no candidate instruments found.")
            return

        spreads_info = []
        chunk_size = 25
        for i in range(0, len(candidate_symbols), chunk_size):
            chunk = candidate_symbols[i:i + chunk_size]
            instruments_str = ",".join(chunk)
            r = PricingInfo(accountID=ACCOUNT_ID, params={"instruments": instruments_str})
            try:
                resp = self.client.request(r)
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
                self.log(f"Discovery pricing error: {e}")

        if not spreads_info:
            self.log("Discovery: no pricing info for candidates.")
            return

        filtered = [
            (sym, spread_ratio)
            for sym, spread_ratio, mid in spreads_info
            if spread_ratio < 0.0005
        ]

        if not filtered:
            self.log("Discovery: no tight-spread candidates.")
            return

        filtered.sort(key=lambda x: x[1])
        selected = [sym for sym, _ in filtered[:MAX_DYNAMIC_SYMBOLS]]

        self.dynamic_symbols = selected
        self.log(f"Discovery: dynamic symbols set to {selected}")
        self.ensure_market_states()

    # --------------------------------------------------------
    # PRICES + ACCOUNT
    # --------------------------------------------------------

    def fetch_prices(self):
        if not self.connected:
            return

        self.ensure_market_states()
        symbols = self.get_active_symbols()
        if not symbols:
            return

        instruments = ",".join(symbols)
        r = PricingInfo(accountID=ACCOUNT_ID, params={"instruments": instruments})

        try:
            resp = self.client.request(r)
            for p in resp["prices"]:
                sym = p["instrument"]
                if sym not in self.markets:
                    continue
                bid = float(p["bids"][0]["price"])
                ask = float(p["asks"][0]["price"])
                mid = (bid + ask) / 2
                m = self.markets[sym]
                prev = m.last if m.last > 0 else mid
                m.last = mid

                change = abs(mid - prev)
                m.atr = 0.9 * m.atr + 0.1 * change if m.atr > 0 else change
        except Exception as e:
            self.log(f"Pricing error: {e}")

    def get_account_summary(self):
        if not self.connected:
            return None
        try:
            r = AccountSummary(accountID=ACCOUNT_ID)
            acc = self.client.request(r)["account"]
            nav = float(acc["NAV"])
            if self.daily_nav_start is None:
                self.daily_nav_start = nav
            self.pnl_curve.append(nav)
            return acc
        except Exception as e:
            self.log(f"AccountSummary error: {e}")
            return None

    def check_daily_loss_guard(self, nav: float) -> bool:
        start = self.daily_nav_start
        if start is None:
            return False
        dd_pct = (start - nav) / start * 100.0
        if dd_pct >= MAX_DAILY_LOSS_PCT:
            self.log(f"DAILY LOSS LIMIT HIT ({dd_pct:.2f}%), stopping trading.")
            self.running = False
            return True
        return False

    def reset_hour_if_needed(self):
        now = datetime.now(timezone.utc)
        if now - self.hour_start >= timedelta(hours=1):
            self.hour_start = now
            self.trades_this_hour = 0

    # --------------------------------------------------------
    # INTELLIGENCE
    # --------------------------------------------------------

    def compute_momentum(self, m: MarketState) -> float:
        if m.last_for_mom == 0:
            return 0.0
        return (m.last - m.last_for_mom) / m.last_for_mom

    def update_regime(self, m: MarketState):
        mom = self.compute_momentum(m)
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

    def multi_tf_momentum(self, m: MarketState) -> float:
        mom1 = self.compute_momentum(m)
        mom5 = m.mom_ema
        return 0.7 * mom1 + 0.3 * mom5

    def symbol_bias(self, symbol: str) -> float:
        if symbol.startswith("EUR_"): return 0.03
        if symbol.startswith("GBP_"): return 0.02
        if symbol.startswith("USD_JPY"): return -0.01
        if symbol.startswith("XAU_"): return 0.05
        return 0.0

    def regime_intelligence(self, m: MarketState):
        if m.regime == "LOW_VOL":
            return {"risk_mult": 1.1, "signal_sensitivity": 0.8}
        if m.regime == "HIGH_VOL":
            return {"risk_mult": 0.6, "signal_sensitivity": 1.4}
        if m.regime == "UP_TREND":
            return {"bias": 0.25}
        if m.regime == "DOWN_TREND":
            return {"bias": -0.25}
        return {"risk_mult": 1.0, "signal_sensitivity": 1.0}

    def compute_score_components(self, m: MarketState, spread: float):
        mom = self.multi_tf_momentum(m)
        bias = self.symbol_bias(m.symbol)

        regime_score = 0.25 if m.regime == "UP_TREND" else -0.25 if m.regime == "DOWN_TREND" else 0.0

        vol_score = 0.2 if 0.0002 < m.vol_ema < 0.002 else -0.2 if m.vol_ema >= 0.002 else 0.0

        wins = self.memory.get(m.symbol, {"wins": 0})["wins"]
        losses = self.memory.get(m.symbol, {"losses": 0})["losses"]
        memory_score = (wins - losses) / max(1, wins + losses)

        momentum_score = mom * 60.0

        spread_penalty = -0.3 if spread > m.last * 0.0004 else 0.0

        return momentum_score, regime_score + bias, vol_score + spread_penalty, memory_score

    def compute_final_score(self, m: MarketState, spread: float) -> float:
        momentum_score, regime_score, volatility_score, memory_score = self.compute_score_components(m, spread)

        ensemble = (
            0.40 * momentum_score +
            0.20 * regime_score +
            0.15 * volatility_score +
            0.10 * memory_score +
            0.15 * m.alpha
        ) / 5.0

        ri = self.regime_intelligence(m)
        ensemble *= ri.get("signal_sensitivity", 1.0)
        ensemble += ri.get("bias", 0.0)

        return max(-3.0, min(3.0, ensemble))

    def score_to_action(self, score: float, threshold: float = 0.04):
        if score > threshold:
            return "BUY"
        if score < -threshold:
            return "SELL"
        return None

    def decay_alpha_all(self):
        for m in self.markets.values():
            m.alpha *= 0.95
            m.alpha_ema_pnl *= 0.95

    # --------------------------------------------------------
    # EXECUTION
    # --------------------------------------------------------

    def compute_units(self, m: MarketState, nav: float) -> int:
        vol = m.vol_ema if m.vol_ema > 0 else 0.0005
        risk_factor = min(2.0, max(0.5, 0.5 / (vol + 1e-6)))
        equity_scale = min(2.0, max(0.5, nav / (self.daily_nav_start or nav)))
        regime_mult = 1.2 if m.regime == "LOW_VOL" else 0.8 if m.regime == "HIGH_VOL" else 1.0

        is_dynamic = m.symbol not in BASE_SYMBOLS
        dynamic_scale = 0.7 if is_dynamic else 1.0

        base_notional = nav * (BASE_RISK_PCT / 100.0)
        notional = base_notional * risk_factor * equity_scale * regime_mult * dynamic_scale
        if m.last <= 0:
            return 0
        return int(max(100, notional / m.last))

    def place_order(self, m: MarketState, side: str, nav: float):
        now = datetime.now(timezone.utc)
        if m.last_trade_time and (now - m.last_trade_time).total_seconds() < COOLDOWN_SECONDS:
            self.log(f"Cooldown active for {m.symbol}, skipping.")
            return

        self.reset_hour_if_needed()
        if self.trades_this_hour >= MAX_TRADES_PER_HOUR:
            self.log("Max trades per hour reached, skipping.")
            return

        units = self.compute_units(m, nav)
        if units <= 0:
            self.log(f"Units <= 0 for {m.symbol}, skip.")
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
            self.client.request(r)
            self.log(f"ORDER: {side} {units} {m.symbol} @ {price:.5f}")
            self.trades_this_hour += 1
            m.last_trade_time = now

            trade_rec = {
                "time": now.isoformat(),
                "symbol": m.symbol,
                "side": side,
                "units": units,
                "price": price,
                "sl": sl_price,
                "tp": tp_price
            }
            self.log_trade(trade_rec)
        except Exception as e:
            self.log(f"ORDER FAILED {m.symbol}: {e}")

    # --------------------------------------------------------
    # CYCLE
    # --------------------------------------------------------

    def run_cycle(self):
        with self.lock:
            self.ensure_connection()
            if not self.connected:
                self.log("Not connected, skipping cycle.")
                return

            self.discover_markets()
            self.ensure_market_states()

            self.fetch_prices()
            acc = self.get_account_summary()
            if not acc:
                return

            nav = float(acc["NAV"])
            if self.check_daily_loss_guard(nav):
                return

            self.log("Cycle Start")

            for m in self.markets.values():
                if m.last == 0:
                    continue

                if m.last_for_mom == 0:
                    m.last_for_mom = m.last

                self.update_regime(m)

                spread_est = m.atr * 0.5 if m.atr > 0 else m.last * 0.0002

                quality = 0
                if abs(m.mom_ema) > 0.0004: quality += 1
                if 0.00015 < m.vol_ema < 0.003: quality += 1
                if spread_est < m.last * 0.0004: quality += 1
                if m.atr < m.last * 0.003: quality += 1

                score = self.compute_final_score(m, spread_est)

                self.log(f"{m.symbol} | Regime={m.regime} | Score={score:.3f} | Quality={quality}")

                if quality < 3:
                    self.log(f"Low-quality setup on {m.symbol}, skipping.")
                    continue

                action = self.score_to_action(score)

                if action:
                    self.place_order(m, action, nav)

            self.decay_alpha_all()
            self.save_state()

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    def run_forever(self):
        self.log("Imperium Engine starting...")
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                self.log(f"Cycle error: {e}")
            time.sleep(CYCLE_INTERVAL_SECONDS)
        self.log("Imperium Engine stopped.")

    def stop(self):
        self.running = False


# ============================================================
# ENTRY POINT
# ============================================================

engine = ImperiumEngine()

def handle_signal(signum, frame):
    engine.log(f"Received signal {signum}, stopping engine...")
    engine.stop()

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if __name__ == "__main__":
    engine.run_forever()
