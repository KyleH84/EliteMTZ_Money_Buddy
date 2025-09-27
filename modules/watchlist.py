# modules/watchlist.py
# Provides read_watchlist / write_watchlist / add_to_watchlist / remove_from_watchlist
import os, csv
from typing import List
WATCHLIST_CSV = os.path.join('Data', 'watchlist.csv')

try:
    import duckdb
    _HAVE_DUCK = True
except Exception:
    _HAVE_DUCK = False

DB_PATH = os.path.join('Data', 'watchlist.duckdb')

def _ensure_dirs():
    os.makedirs('Data', exist_ok=True)

def _ensure_duckdb():
    if not _HAVE_DUCK:
        return None
    con = duckdb.connect(DB_PATH, read_only=False)
    con.execute("""CREATE TABLE IF NOT EXISTS watchlist(
        symbol TEXT PRIMARY KEY,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );""")
    return con

# Public API expected by UI
def read_watchlist() -> List[str]:
    _ensure_dirs()
    # Prefer DuckDB
    if _HAVE_DUCK:
        con = _ensure_duckdb()
        rows = con.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
        con.close()
        return [r[0] for r in rows]
    # Fallback CSV
    if not os.path.exists(WATCHLIST_CSV):
        return []
    with open(WATCHLIST_CSV, newline='') as f:
        return [row[0] for row in csv.reader(f) if row]

def write_watchlist(symbols: List[str]):
    _ensure_dirs()
    symbols = sorted(set(s.upper() for s in symbols if s))
    if _HAVE_DUCK:
        con = _ensure_duckdb()
        con.execute("DELETE FROM watchlist")
        con.executemany("INSERT INTO watchlist(symbol) VALUES (?)", [(s,) for s in symbols])
        con.close()
        return
    with open(WATCHLIST_CSV, 'w', newline='') as f:
        w = csv.writer(f); [w.writerow([s]) for s in symbols]

def add_to_watchlist(symbol: str):
    sym = (symbol or "").upper().strip()
    if not sym: return
    if _HAVE_DUCK:
        con = _ensure_duckdb()
        con.execute("INSERT OR REPLACE INTO watchlist(symbol) VALUES (?)", [sym])
        con.close()
    else:
        cur = set(read_watchlist()); cur.add(sym); write_watchlist(list(cur))

def remove_from_watchlist(symbol: str):
    sym = (symbol or "").upper().strip()
    if not sym: return
    if _HAVE_DUCK:
        con = _ensure_duckdb()
        con.execute("DELETE FROM watchlist WHERE symbol = ?", [sym])
        con.close()
    else:
        cur = set(read_watchlist()); cur.discard(sym); write_watchlist(list(cur))