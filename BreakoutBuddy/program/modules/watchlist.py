from __future__ import annotations
from typing import Iterable, List
import duckdb

def ensure_watchlist(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker VARCHAR,
            added_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note VARCHAR
        )
    """)

def _norm_tickers(tickers: Iterable[str] | None) -> List[str]:
    out: List[str] = []
    for t in (tickers or []):
        if not t:
            continue
        t2 = str(t).strip().upper()
        if t2 and t2 not in out:
            out.append(t2)
    return out

def add_to_watchlist(conn, tickers: Iterable[str] | None) -> int:
    ensure_watchlist(conn)
    syms = _norm_tickers(tickers)
    if not syms:
        return 0
    n = 0
    for t in syms:
        try:
            conn.execute("INSERT INTO watchlist (ticker) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM watchlist WHERE ticker = ?)", [t, t])
            n += 1
        except Exception:
            pass
    return n

def remove_from_watchlist(conn, tickers: Iterable[str] | None) -> int:
    ensure_watchlist(conn)
    syms = _norm_tickers(tickers)
    if not syms:
        return 0
    q = "DELETE FROM watchlist WHERE ticker IN (" + ",".join(["?"] * len(syms)) + ")"
    conn.execute(q, syms)
    return len(syms)

def list_watchlist(conn) -> list[str]:
    ensure_watchlist(conn)
    try:
        df = conn.execute("SELECT ticker FROM watchlist ORDER BY ticker").fetchdf()
        return [str(x).upper() for x in df["ticker"].tolist()]
    except Exception:
        return []
