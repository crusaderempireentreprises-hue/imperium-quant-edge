from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json

LOG_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "imperium_logs")
ENGINE_LOG = os.path.join(LOG_DIR, "engine.log")
TRADES_FILE = os.path.join(LOG_DIR, "trades.jsonl")
STATE_FILE = os.path.join(LOG_DIR, "state.json")

app = FastAPI(title="Imperium API v3.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def read_file_lines(path, max_lines=500):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()[-max_lines:]
    except:
        return []

def read_jsonl(path, max_lines=200):
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-max_lines:]:
                try:
                    out.append(json.loads(line))
                except:
                    pass
    except:
        pass
    return out

def read_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

@app.get("/status")
def status():
    state = read_state()
    logs = read_file_lines(ENGINE_LOG, 5)
    return {
        "status": "running",
        "last_log": logs[-1].strip() if logs else "No logs",
        "dynamic_symbols": state.get("dynamic_symbols", []),
        "pnl_points": len(state.get("pnl_curve", [])),
    }

@app.get("/pnl")
def pnl():
    state = read_state()
    return {"pnl_curve": state.get("pnl_curve", [])}

@app.get("/universe")
def universe():
    state = read_state()
    return {
        "dynamic_symbols": state.get("dynamic_symbols", []),
        "memory": state.get("memory", {})
    }

@app.get("/trades")
def trades():
    return {"trades": read_jsonl(TRADES_FILE, 200)}

@app.get("/logs")
def logs():
    lines = read_file_lines(ENGINE_LOG, 300)
    return {"logs": [l.strip() for l in lines]}

@app.get("/state")
def full_state():
    return read_state()

@app.get("/rl")
def rl_state():
    state = read_state()
    return {"rl_q": state.get("rl_q", {})}

@app.get("/symbols")
def symbols():
    state = read_state()
    return state.get("symbol_snapshot", {})

@app.get("/rl_timeseries")
def rl_timeseries():
    state = read_state()
    return state.get("rl_history", {})
