from __future__ import annotations
import pandas as pd

# Adaptive insert (unchanged behavior) + richer summary helpers

def rsi_edge_tracker(conn, df_snapshot: pd.DataFrame, ts=None):
    if df_snapshot is None or df_snapshot.empty:
        return
    if ts is None:
        ts = pd.Timestamp.utcnow()
    keep = df_snapshot.copy()
    keep = keep.rename(columns={
        "Close":"close","RSI2":"rsi2","RSI4":"rsi4","ConnorsRSI":"connors",
        "PctFrom200d":"pct_from_200d","RelSPY":"rel_spy","RVOL":"rvol",
        "ATR":"atr","SqueezeHint":"squeeze_hint","CrowdRisk":"crowd_risk","RetailChaseRisk":"retail_chase_risk"
    })
    keep["ts"] = ts
    keep = keep.rename(columns={"Ticker":"ticker"})
    desired = ["ts","ticker","close","rsi2","rsi4","connors","pct_from_200d","rel_spy","rvol","atr","squeeze_hint","crowd_risk","retail_chase_risk"]
    # Ensure table & match schema
    try:
        cols_info = conn.execute("PRAGMA table_info('scans')").fetchdf()
        schema_cols = [c for c in cols_info["name"].tolist()] if "name" in cols_info.columns else []
        if not schema_cols:
            raise Exception("no_schema")
    except Exception:
        conn.execute("""CREATE TABLE IF NOT EXISTS scans (
            ts TIMESTAMP,
            ticker VARCHAR,
            close DOUBLE,
            rsi2 DOUBLE, rsi4 DOUBLE, connors DOUBLE,
            pct_from_200d DOUBLE,
            rel_spy DOUBLE,
            rvol DOUBLE,
            atr DOUBLE,
            squeeze_hint DOUBLE,
            crowd_risk DOUBLE,
            retail_chase_risk DOUBLE
        )""")
        schema_cols = desired[:]
    insert_cols = [c for c in desired if c in schema_cols and c in keep.columns]
    if not insert_cols:
        return
    conn.register("tmp_df", keep[insert_cols])
    sql = "INSERT INTO scans ({cols}) SELECT {cols} FROM tmp_df".format(cols=",".join(insert_cols))
    conn.execute(sql)
    conn.unregister("tmp_df")

def _to_list(series: pd.Series) -> list[str]:
    vals = [str(x) for x in series.dropna().tolist()]
    # Keep unique order
    seen = set()
    out = []
    for v in vals:
        if v not in seen:
            out.append(v); seen.add(v)
    return out

def render_edge_summary(df_snapshot: pd.DataFrame) -> pd.DataFrame:
    """Return Edge, Count, and TopTickers (comma‑separated) for quick glance."""
    df = df_snapshot.copy()
    edges = []
    def add_edge(name, mask):
        tickers = _to_list(df.loc[mask, "Ticker"] if name != "SqueezeHints" else df.loc[mask > 0, "Ticker"])
        edges.append({
            "Edge": name,
            "Count": int(len(tickers)),
            "TopTickers": ", ".join(tickers[:10])
        })
    add_edge("RSI2<5", df["RSI2"] < 5)
    add_edge("RSI2<10", df["RSI2"] < 10)
    add_edge("RSI4<10", df["RSI4"] < 10)
    add_edge("Connors<25", df["ConnorsRSI"] < 25)
    add_edge("Pct<200d", df["PctFrom200d"] < 0)
    add_edge("SqueezeHints", df["SqueezeHint"])
    return pd.DataFrame(edges)

def tickers_for_edge(df_snapshot: pd.DataFrame, edge_name: str) -> pd.DataFrame:
    """Return the exact tickers (and key columns) that match a given edge."""
    df = df_snapshot.copy()
    if edge_name == "RSI2<5":
        m = df["RSI2"] < 5
    elif edge_name == "RSI2<10":
        m = df["RSI2"] < 10
    elif edge_name == "RSI4<10":
        m = df["RSI4"] < 10
    elif edge_name == "Connors<25":
        m = df["ConnorsRSI"] < 25
    elif edge_name == "Pct<200d":
        m = df["PctFrom200d"] < 0
    elif edge_name == "SqueezeHints":
        m = df["SqueezeHint"] > 0
    else:
        m = df["RSI2"] < -1  # empty
    cols = ["Ticker","Close","ChangePct","RSI2","RSI4","ConnorsRSI","RelSPY","RVOL","PctFrom200d","SqueezeHint"]
    cols = [c for c in cols if c in df.columns]
    out = df.loc[m, cols].copy()
    out = out.sort_values(by=[c for c in ["RSI2","ConnorsRSI","ChangePct"] if c in out.columns], ascending=[True, True, False])
    return out
