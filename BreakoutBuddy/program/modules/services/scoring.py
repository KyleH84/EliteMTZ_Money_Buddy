from __future__ import annotations
import pandas as pd

def _ensure_rank_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Combined" not in df.columns:
        pu = pd.to_numeric(df.get("P_up", 0.5), errors="coerce").fillna(0.5)
        rel = pd.to_numeric(df.get("RelSPY", 0.0), errors="coerce").fillna(0.0)
        rv  = pd.to_numeric(df.get("RVOL", 1.0), errors="coerce").fillna(1.0)
        df["Combined"] = (pu * 70.0 + rel * 10.0 + (rv - 1.0) * 20.0).clip(0, 100)
    try:
        from modules.services import agents_service as AS
        df = AS.enrich_scores(df)
    except Exception:
        pass
    sort_col = "Combined_with_agents" if "Combined_with_agents" in df.columns else "Combined"
    df = df.sort_values(by=[sort_col], ascending=False).reset_index(drop=True)
    return df

def rank_now(arg) -> pd.DataFrame | tuple:
    """Flexible entry:
    - If arg is a DataFrame: return ranked DataFrame (backwards compatible).
    - If arg is a dict-like settings: build snapshot, compute ranking, and return
      (snapshot_df, regime_dict, ranked_df, auc_placeholder, model_placeholder).
    """
    import pandas as pd
    import math

    # DataFrame path
    if isinstance(arg, pd.DataFrame):
        return _ensure_rank_cols(arg)

    # Dict-like path (used by app_main rank_now_fn)
    try:
        settings = dict(arg)
    except Exception:
        settings = {}
    try:
        uni_n = int(settings.get("universe_size", 300))
        top_n = int(settings.get("top_n", 25))
    except Exception:
        uni_n, top_n = 300, 25

    try:
        from modules import data as data_mod
        from modules import regime as regime_mod
        # Universe + snapshot
        tickers = data_mod.list_universe(uni_n)
        snap = data_mod.pull_enriched_snapshot(tickers)
        ranked = _ensure_rank_cols(snap)
        if top_n and top_n > 0 and top_n < len(ranked):
            ranked = ranked.head(top_n)
        # Regime info
        try:
            regime = regime_mod.compute_regime()
        except Exception:
            regime = {}
        return snap, regime, ranked, None, None
    except Exception as e:
        # Fallback: return empty tuple rather than crash
        return pd.DataFrame(), {}, pd.DataFrame(), None, None
