
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional, Sequence
import pandas as pd
import duckdb

# Columns we persist; extra columns are ignored safely.
FEATURE_COLS: Sequence[str] = [
    "Ticker","Close","ChangePct","RelSPY","RVOL","RSI4","ConnorRSI",
    "ATR","ADX","SqueezeOn","SqueezeHint","GapPct"
]

def _ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS features_history (
            as_of TIMESTAMP,
            Ticker VARCHAR,
            Close DOUBLE,
            ChangePct DOUBLE,
            RelSPY DOUBLE,
            RVOL DOUBLE,
            RSI4 DOUBLE,
            ConnorRSI DOUBLE,
            ATR DOUBLE,
            ADX DOUBLE,
            SqueezeOn INTEGER,
            SqueezeHint DOUBLE,
            GapPct DOUBLE
        );
    """)
    con.execute("""
        
        CREATE OR REPLACE VIEW features_latest AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT
                as_of, Ticker, Close, ChangePct, RelSPY, RVOL, RSI4,
                ConnorRSI, ATR, ADX, SqueezeOn, SqueezeHint, GapPct,
                ROW_NUMBER() OVER (PARTITION BY Ticker ORDER BY as_of DESC) AS rn
            FROM features_history
        ) WHERE rn = 1;
             
    """)

def persist_features(df: pd.DataFrame, db_path: Path | str, *, asof: Optional[pd.Timestamp] = None) -> int:
    """Append snapshot features into DuckDB and refresh features_latest view.
    Returns the number of rows written.
    """
    if df is None or df.empty or "Ticker" not in df.columns:
        return 0
    keep = [c for c in FEATURE_COLS if c in df.columns] + ["Ticker"]
    keep = list(dict.fromkeys(keep))  # dedupe while preserving order
    tmp = df[keep].copy()
    if tmp.empty:
        return 0
    asof = pd.Timestamp.utcnow().floor("min") if asof is None else pd.Timestamp(asof)
    tmp.insert(0, "as_of", asof)
    con = duckdb.connect(str(db_path))
    _ensure_table(con)
    con.register("tmp_df", tmp)
    con.execute("INSERT INTO features_history SELECT * FROM tmp_df")
    con.unregister("tmp_df")
    con.close()
    return len(tmp)

def load_features(db_path: Path | str, *, tickers: Optional[Iterable[str]] = None, latest: bool = True) -> pd.DataFrame:
    con = duckdb.connect(str(db_path))
    _ensure_table(con)
    if latest:
        if tickers:
            q = "SELECT * FROM features_latest WHERE upper(Ticker) IN (%s)" % ",".join(['?']*len(list(tickers)))
            df = con.execute(q, [t.upper() for t in tickers]).df()
        else:
            df = con.execute("SELECT * FROM features_latest").df()
    else:
        if tickers:
            q = "SELECT * FROM features_history WHERE upper(Ticker) IN (%s) ORDER BY asof DESC" % ",".join(['?']*len(list(tickers)))
            df = con.execute(q, [t.upper() for t in tickers]).df()
        else:
            df = con.execute("SELECT * FROM features_history ORDER BY asof DESC").df()
    con.close()
    return df
