# BreakoutBuddy/program/modules/watchlist.py (patched)
# Provides read_watchlist / write_watchlist / add_to_watchlist / remove_from_watchlist
import os, csv
from typing import List

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Data")
os.makedirs(DATA_DIR, exist_ok=True)

CSV_PATH = os.path.join(DATA_DIR, "watchlist.csv")
DB_PATH  = os.path.join(DATA_DIR, "watchlist.duckdb")

try:
    import duckdb
    HAVE_DUCK = True
except Exception:
    HAVE_DUCK = False

def _ensure_duck():
    if not HAVE_DUCK: return None
    con = duckdb.connect(DB_PATH, read_only=False)
    con.execute("""CREATE TABLE IF NOT EXISTS watchlist(
        symbol TEXT PRIMARY KEY,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );""" )
    return con

def read_watchlist() -> List[str]:
    if HAVE_DUCK:
        con = _ensure_duck()
        rows = con.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
        con.close()
        return [r[0] for r in rows]
    if not os.path.exists(CSV_PATH): return []
    with open(CSV_PATH, newline='') as f:
        return [row[0] for row in csv.reader(f) if row]

def write_watchlist(symbols: List[str]):
    symbols = sorted(set(s.upper() for s in symbols if s))
    if HAVE_DUCK:
        con = _ensure_duck()
        con.execute("DELETE FROM watchlist")
        con.executemany("INSERT INTO watchlist(symbol) VALUES (?)", [(s,) for s in symbols])
        con.close()
        return
    with open(CSV_PATH, 'w', newline='') as f:
        w = csv.writer(f); [w.writerow([s]) for s in symbols]

def add_to_watchlist(symbol: str):
    s = (symbol or "").upper().strip()
    if not s: return
    if HAVE_DUCK:
        con = _ensure_duck()
        con.execute("INSERT OR REPLACE INTO watchlist(symbol) VALUES (?)", [s])
        con.close()
    else:
        cur = set(read_watchlist()); cur.add(s); write_watchlist(list(cur))

def remove_from_watchlist(symbol: str):
    s = (symbol or "").upper().strip()
    if not s: return
    if HAVE_DUCK:
        con = _ensure_duck()
        con.execute("DELETE FROM watchlist WHERE symbol = ?", [s])
        con.close()
    else:
        cur = set(read_watchlist()); cur.discard(s); write_watchlist(list(cur))