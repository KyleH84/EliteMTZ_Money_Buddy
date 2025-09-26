from __future__ import annotations
from typing import Any, List, Dict
from pathlib import Path
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import yfinance as yf
from modules.services.newswire_local import (
    load_news_csv, save_news_csv, append_rows,
    filter_recent, list_unique_tickers, parse_ticker_text
)
from modules.services.enrich import enrich_features

def _extras_dir() -> Path:
    here = Path(__file__).resolve()
    extras = here.parents[2] / "extras"
    extras.mkdir(exist_ok=True, parents=True)
    return extras

def _default_csv_path() -> Path:
    return _extras_dir() / "elite_news.csv"

def _discover_universe(max_count: int = 300) -> List[str]:
    extras = _extras_dir()
    cand = extras / "symbols.csv"
    if cand.exists():
        try:
            df = pd.read_csv(cand)
            if "Ticker" in df.columns:
                syms = [str(x).upper() for x in df["Ticker"].dropna().astype(str).tolist()]
                syms = [s for s in syms if s and s != "TICKER"]
                return sorted(set(syms))[:max_count]
        except Exception:
            pass
    cache_dir = (Path(__file__).resolve().parents[3] / "Data" / "cache" / "ohlcv")
    syms = []
    if cache_dir.exists():
        for p in cache_dir.glob("*.csv"):
            name = p.stem
            sym = name.split("_")[0].upper()
            if sym and sym.isascii():
                syms.append(sym)
            if len(syms) >= max_count:
                break
        if syms:
            return sorted(set(syms))[:max_count]
    return ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","AVGO"][:max_count]

def _infer_sign_from_title(title: str) -> str:
    t = (title or "").lower()
    pos = ["beats","beat","raises","upgrade","upgraded","record","surge","soars","jumps","tops","strong","profit","buyback"]
    neg = ["miss","cuts","cut","downgrade","downgraded","slump","falls","sinks","plunge","warns","warning","guidance down","weak"]
    if any(w in t for w in pos) and not any(w in t for w in neg):
        return "+"
    if any(w in t for w in neg) and not any(w in t for w in pos):
        return "-"
    return ""

def _fetch_news_for_ticker(t: str, since_hours: int) -> List[Dict[str, str]]:
    out: List[Dict[str,str]] = []
    try:
        obj = yf.Ticker(t)
        items = getattr(obj, "news", []) or []
        now = datetime.now(timezone.utc)
        cutoff = now - pd.Timedelta(hours=since_hours)
        for it in items:
            title = it.get("title","")
            link = it.get("link","")
            src  = it.get("publisher") or it.get("provider","Yahoo")
            ts = it.get("providerPublishTime") or it.get("published") or None
            dt_utc = None
            if ts is not None:
                try:
                    dt_utc = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                except Exception:
                    try:
                        dt_utc = pd.to_datetime(ts, utc=True).to_pydatetime()
                    except Exception:
                        dt_utc = None
            if dt_utc is None:
                dt_utc = now
            if dt_utc < cutoff:
                continue
            sign = _infer_sign_from_title(title)
            out.append({
                "Date": dt_utc.strftime("%Y-%m-%d %H:%M:%S%z"),
                "Company": "",
                "Ticker": t,
                "Sign": sign,
                "Headline": title,
                "Link": link,
                "Source": src or "Yahoo",
            })
    except Exception:
        pass
    return out

def render_elitenewsbot_tab(*, settings: Any = None) -> None:
    st.subheader("EliteNewsBot — Auto News Scan")
    st.caption("Fetch last-12h news via yfinance, populate elite_news.csv, and scan those tickers through BB.")

    csv_path = _default_csv_path()
    lookback = st.slider("News lookback (hours)", 6, 24, 12, 2)
    max_universe = st.slider("Universe size (scan up to N tickers)", 50, 600, 250, 50)
    throttle = st.slider("Per-ticker delay (seconds)", 0.0, 0.5, 0.05, 0.05)

    universe_mode = st.radio("Universe source", ["Auto-discover", "Manual list"], horizontal=True)
    if universe_mode == "Manual list":
        raw = st.text_area("Tickers", "AAPL, MSFT, NVDA", height=100)
        universe = parse_ticker_text(raw)[:max_universe]
    else:
        universe = _discover_universe(max_count=max_universe)

    colA, colB, colC = st.columns(3)
    with colA:
        do_fetch = st.button("Fetch & populate news CSV", type="primary")
    with colB:
        df_existing = load_news_csv(csv_path=csv_path)
        st.download_button("Download elite_news.csv", data=df_existing.to_csv(index=False).encode("utf-8"), file_name="elite_news.csv")
    with colC:
        do_scan = st.button("Run scanner on news tickers")

    if do_fetch:
        st.write(f"Scanning {len(universe)} tickers for news in last {lookback}h...")
        collected: List[Dict[str,str]] = []
        prog = st.progress(0.0)
        for i, sym in enumerate(universe):
            collected.extend(_fetch_news_for_ticker(sym, since_hours=lookback))
            if throttle:
                time.sleep(throttle)
            if i % 10 == 0:
                prog.progress((i+1) / max(1, len(universe)))
        if collected:
            df = append_rows(collected, csv_path=csv_path)
            st.success(f"Collected {len(collected)} items. CSV now has {len(df)} rows.")
        else:
            st.info("No fresh items found in the selected universe/interval.")

    df_news = load_news_csv(csv_path=csv_path)
    df_recent = filter_recent(df_news, hours=lookback)
    st.caption(f"Recent news in CSV (last {lookback}h): {len(df_recent)}")
    if not df_recent.empty:
        st.dataframe(df_recent.head(200), use_container_width=True, hide_index=True)

    tickers = list_unique_tickers(df_recent)
    with st.expander("Tickers derived from recent news (edit if needed)"):
        txt = st.text_area("Ticker list", value=", ".join(tickers), height=100)
        tickers = parse_ticker_text(txt)
        st.caption(f"{len(tickers)} tickers after parsing.")

    if do_scan and tickers:
        base = pd.DataFrame({"Ticker": tickers})
        snap = enrich_features(tickers, base_df=base)
        latest = (df_recent.sort_values("Date", ascending=False)
                            .groupby("Ticker", as_index=False)
                            .first()[["Ticker","Headline","Sign","Source"]]
                            .rename(columns={"Headline":"LatestHeadline"}))
        out = snap.merge(latest, on="Ticker", how="left")
        cols = [c for c in ["Ticker","Close","ChangePct","RVOL","RSI4","ConnorsRSI","RelSPY","P_up","LatestHeadline","Sign","Source"] if c in out.columns]
        if cols: out = out[cols]
        st.caption(f"Rows: {len(out)}")
        st.dataframe(out, use_container_width=True, hide_index=True)
        st.download_button("Download elitenewsbot_scan.csv", data=out.to_csv(index=False).encode("utf-8"), file_name="elitenewsbot_scan.csv")
