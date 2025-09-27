
import pandas as pd
import numpy as np
import yfinance as yf

# --------------------------------------------------------------------
# Main feature enrichment
# --------------------------------------------------------------------

def ensure_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure required feature columns exist and are populated.
    If any are missing or NaN, fetch from yfinance and compute."""
    if df is None or df.empty:
        return df

    if "Ticker" not in df.columns:
        return df

    tickers = df["Ticker"].dropna().astype(str).str.upper().unique().tolist()
    if not tickers:
        return df

    required = ["RelSPY", "ConnorsRSI", "SqueezeHint", "P_up",
                "RVOL", "RSI4", "ChangePct", "Close"]

    # If any required column missing, create placeholder for the isna check
    for col in required:
        if col not in df.columns:
            df[col] = np.nan

    missing_mask = df[required].isna() | df[required].eq("None")
    missing_tickers = df.loc[missing_mask.any(axis=1), "Ticker"].astype(str).str.upper().unique().tolist()

    if missing_tickers:
        try:
            fetched = fetch_features_for(missing_tickers)
            if not fetched.empty:
                # Drop possibly stale columns so merge prefers fetched
                df = df.drop(columns=[c for c in required if c in df.columns], errors="ignore")
                df = df.merge(fetched, on="Ticker", how="left")
        except Exception as e:
            print(f"[enrich] fetch failed: {e}")

    # Final cleanup
    for col in required:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce") if col not in ("SqueezeHint",) else df[col]
    return df


# --------------------------------------------------------------------
# Fetch helper
# --------------------------------------------------------------------

def fetch_features_for(tickers):
    """Fetch simple feature set from yfinance for tickers + SPY."""
    import datetime

    end = datetime.date.today()
    start = end - datetime.timedelta(days=30)

    # Always include SPY for relative strength
    yf_tickers = sorted(set([t.strip().upper() for t in tickers if t]) | {"SPY"})
    if not yf_tickers:
        return pd.DataFrame(columns=["Ticker", "Close", "ChangePct", "RelSPY", "RSI4", "ConnorsRSI", "RVOL", "P_up", "SqueezeHint"])

    data = yf.download(yf_tickers, start=start, end=end, progress=False, group_by="ticker")

    if isinstance(data.columns, pd.MultiIndex):
        closes = pd.DataFrame({t: data[t].get("Close") for t in yf_tickers if "Close" in data[t]})
        vols = pd.DataFrame({t: data[t].get("Volume") for t in yf_tickers if "Volume" in data[t]})
    else:
        closes = data["Close"].to_frame()
        vols = data["Volume"].to_frame()

    latest = []
    for t in [x for x in yf_tickers if x != "SPY"]:
        s = closes.get(t, pd.Series(dtype=float)).dropna()
        v = vols.get(t, pd.Series(dtype=float)).dropna()
        if s.empty:
            latest.append({"Ticker": t})
            continue

        close = s.iloc[-1]
        change_pct = (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s) > 1 else 0.0

        spy_s = closes.get("SPY", pd.Series(dtype=float)).dropna()
        relspy = (s.pct_change().iloc[-1] - spy_s.pct_change().iloc[-1]) if len(s) > 1 and len(spy_s) > 1 else np.nan

        # RSI4 (simple)
        delta = s.diff()
        gain = delta.clip(lower=0).rolling(4).mean()
        loss = -delta.clip(upper=0).rolling(4).mean()
        rs = gain / (loss + 1e-9)
        rsi4 = 100 - (100 / (1 + rs.iloc[-1])) if not rs.dropna().empty else 50

        # RVOL (5d)
        rvol = v.iloc[-1] / v.rolling(5).mean().iloc[-1] if len(v) >= 5 and v.rolling(5).mean().iloc[-1] else 1.0

        latest.append(dict(
            Ticker=t,
            Close=float(close),
            ChangePct=round(float(change_pct), 4),
            RelSPY=round(float(relspy), 4) if pd.notna(relspy) else np.nan,
            RSI4=round(float(rsi4), 2),
            ConnorsRSI=50.0,   # placeholder
            RVOL=round(float(rvol), 3),
            P_up=0.55,         # neutral placeholder
            SqueezeHint=0.0    # placeholder
        ))

    return pd.DataFrame(latest)


# --------------------------------------------------------------------
# Backward-compat shim
# --------------------------------------------------------------------

def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility alias for older code importing `enrich_features`.
    Just calls ensure_features."""
    return ensure_features(df)
