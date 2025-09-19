
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import numpy as np

def _load_settings(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def apply_all_engines(df: pd.DataFrame, settings_path: str | Path = "extras/engines_settings.json", app_path: str | Path = "extras/app_settings.json") -> pd.DataFrame:
    if df is None or df.empty or "Ticker" not in df.columns:
        return df
    settings = _load_settings(settings_path)
    app = _load_settings(app_path)
    out = df.copy()
    e_breakout = bool(app.get("enable_breakout", True))
    e_crosser = bool(app.get("enable_crosser", True))
    e_box = bool(app.get("enable_box", True))
    e_fade = bool(app.get("enable_retail_fade", True))

    def ensure(name, default=0.0):
        if name not in out.columns:
            out[name] = default
        return pd.to_numeric(out[name], errors="coerce").fillna(default)

    close = ensure("Close")
    atr   = ensure("ATR").replace(0, np.nan).fillna(np.nanmedian(ensure("ATR").replace(0,np.nan)))
    rvol  = ensure("RVOL", 1.0)
    rsi2  = ensure("RSI2", 50.0)
    rsi4  = ensure("RSI4", 50.0)
    squeeze = ensure("SqueezeHint", 0.0)
    relspy  = ensure("RelSPY", 0.0)
    hi55  = out["Hi55"] if "Hi55" in out.columns else None
    ema20 = out["EMA20"] if "EMA20" in out.columns else pd.Series(index=out.index, data=np.nan)
    ema50 = out["EMA50"] if "EMA50" in out.columns else pd.Series(index=out.index, data=np.nan)

    # Breakout
    if not e_breakout:
        out["BreakoutOK"] = 0
    else:
        bcfg = settings.get("breakout", {})
        min_rvol = float(bcfg.get("min_rvol", 1.8))
        bbw_pctile_max = float(bcfg.get("bbw_pctile_max", 0.30))
        min_bo_atr = float(bcfg.get("min_breakout_atr", 0.75))
        trendOK = (ema20 > ema50) if (isinstance(ema20, pd.Series) and ema20.notna().any()) else (relspy > 0)
        if hi55 is not None and "ATR" in out.columns:
            breakout_ok = (close > hi55) & (rvol >= min_rvol) & (squeeze <= bbw_pctile_max) & trendOK & (((close - hi55)/atr) >= min_bo_atr)
        else:
            breakout_ok = (rvol >= min_rvol) & (squeeze <= bbw_pctile_max) & trendOK
        out["BreakoutOK"] = breakout_ok.astype(int)

    # Crosser
    if not e_crosser:
        out["CrosserOK"] = 0
    else:
        ccfg = settings.get("crosser", {})
        levels = ccfg.get("levels", [5.0,10.0])
        level_hit = pd.Series(False, index=out.index)
        for L in levels:
            level_hit = level_hit | ((close >= L) & (close.shift(1) < L))
        out["CrosserOK"] = level_hit.astype(int)

    # Box
    if not e_box:
        out["BoxOK"] = 0
    else:
        bxcfg = settings.get("box", {})
        box_ok = (squeeze <= float(bxcfg.get("bbw_pctile_max", 0.20)))
        out["BoxOK"] = box_ok.astype(int)

    # Retail Fade
    if not e_fade:
        out["RetailFadeOK"] = 0
    else:
        fcfg = settings.get("retail_fade", {})
        gap = out["GapPct"] if "GapPct" in out.columns else pd.Series(0.0, index=out.index)
        fade_ok = (gap >= float(fcfg.get("gap_min_pct", 6.0))) & (rsi2 >= float(fcfg.get("rsi2_min", 95.0)))
        out["RetailFadeOK"] = fade_ok.astype(int)

    # Reasons & EngineScore
    reasons = []
    reasons.append(np.where(out.get("BreakoutOK",0)==1, "Breakout55 ✓", ""))
    reasons.append(np.where(out.get("CrosserOK",0)==1, "LevelCross ✓", ""))
    reasons.append(np.where(out.get("BoxOK",0)==1, "BoxSetup ✓", ""))
    reasons.append(np.where(out.get("RetailFadeOK",0)==1, "RetailFade ✓", ""))
    import numpy as _np
    R = _np.vstack(reasons) if reasons else _np.empty((0,len(out)))
    chips = pd.Series(["; ".join([x for x in R[:,i] if x]) for i in range(R.shape[1])] if R.size else [""]*len(out), index=out.index)
    out["EngineReasons"] = chips
    score = (out.get("BreakoutOK",0)*35 + out.get("CrosserOK",0)*20 + out.get("BoxOK",0)*20 + out.get("RetailFadeOK",0)*25)
    out["EngineScore"] = pd.to_numeric(score, errors="coerce").fillna(0).clip(0,100)
    return out
