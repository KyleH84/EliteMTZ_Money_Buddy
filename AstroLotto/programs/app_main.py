from __future__ import annotations
# === Agents Layer: Feature Flag ===
USE_AGENTS = True  # flip False to revert instantly

# === Agents Layer: Imports ===
from datetime import datetime
try:
    from agents.state import RunInputs, RunState, PickSet
    from agents.pipeline import AgentsPipeline
    AGENTS_AVAILABLE = True
except Exception:
    AGENTS_AVAILABLE = False

# === Agents Layer: Adapters (wire to your existing functions) ===
def _etl_fetch(game: str, date: datetime) -> dict:
    return {
        "jackpot": int(get_jackpot_for_game(game)),
        "schedule": {},
    }

def _feature_engineer(game: str, etl: dict, oracle, oracle_gain: float):
    return build_features(game, etl, oracle, oracle_gain)

def _perball_model_score(game: str, features):
    return score_per_ball(game, features)

def _sampler_fn(model_probs: dict, seed: int, temperature: float, pool_size: int):
    raw = sample_candidates(model_probs, seed=seed, temperature=temperature, pool_size=pool_size)
    picks = []
    for r in raw:
        if isinstance(r, dict):
            picks.append(PickSet(white=r.get("white", []), special=r.get("special", 0), meta=r.get("meta", {})))
        else:
            white, special = r
            picks.append(PickSet(white=list(white), special=int(special), meta={}))
    return picks

class _PopularityModel:
    def estimate(self, white, special) -> float:
        return float(estimate_combination_popularity(white, special))

def _oracle_fetchers():
    return {
        "lunar_phase_frac": lambda dt: get_lunar_phase_fraction(dt),
        "kp_3h_max":        lambda dt: get_kp_3h_max(dt),
        "ap_daily":         lambda dt: get_ap_daily(dt),
        "f10_7":            lambda dt: get_f10_7_flux(dt),
        "flare_mx_72h":     lambda dt: get_mx_flare_count_72h(dt),
        "alignment_index":  lambda dt: get_alignment_index(dt),
        "mercury_retro":    lambda dt: is_mercury_retrograde(dt),
        "vix_close":        lambda dt: get_vix_close(dt),
    }

def _freshness_checkers():
    return {
        "jackpot":     lambda: last_jackpot_update_time(),
        "spaceweather":lambda: last_spaceweather_update_time(),
        "markets":     lambda: last_markets_update_time(),
    }

def _make_pipeline():
    return AgentsPipeline(
        etl_fetch=_etl_fetch,
        feature_engineer=_feature_engineer,
        perball_model_score=_perball_model_score,
        sampler_fn=_sampler_fn,
        popularity_model=_PopularityModel(),
        oracle_fetchers=_oracle_fetchers(),
        freshness_checkers=_freshness_checkers(),
        runs_dir="Data/runs"
    )

# === Agents Layer: Predict Hook (call this where you handle Predict button) ===
def run_agents_predict(game: str, mode: str, oracle_gain_override: float | None, seed: int | None, draw_date):
    if not (USE_AGENTS and AGENTS_AVAILABLE):
        return None
    try:
        inputs = RunInputs(
            game=game,
            draw_date=draw_date,
            mode=mode,
            seed=(int(seed) if seed else None),
            oracle_gain_override=(None if (oracle_gain_override is None or oracle_gain_override == 0.0) else float(oracle_gain_override)),
        )
        state = RunState(inputs=inputs)
        p = _make_pipeline()
        state = p.run(state)
        return state
    except Exception as e:
        return e



import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---- Optional Agents integration helpers ----
import importlib as _importlib
def _import_first(_mods):
    for _m in _mods:
        try:
            return _importlib.import_module(_m)
        except Exception:
            continue
    return None
def _call_first(_mod, _fns=("render","main","run")):
    if _mod is None:
        return False
    for _fn in _fns:
        _f = getattr(_mod, _fn, None)
        if callable(_f):
            try:
                _f()
                return True
            except Exception as _e:
                import streamlit as _st
                _st.error(f"Agents page error in {_mod.__name__}.{_fn}(): {_e}")
                return True
    return False

# app_main.py — hot/cold learning + Monte Carlo + diversity badges
import streamlit as st
from astrolotto_temporal_integration import (TemporalControls, apply_temporal_to_weights, apply_temporal_to_vector)
import pandas as pd
import numpy as np
import os
import csv
import json
import math
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import inspect, json, math, re

# Core utilities
from utilities.probability import compute_number_probs, GAME_RULES
from utilities.fallback_predict import predict_frequency_fallback
from utilities.per_ball_ml import train_per_ball_ml, predict_per_ball_ml
from utilities.oracle_engine import OracleSettings, compute_oracle
from utilities.oracle_data import kp_index_recent, solar_flare_activity, moon_phase_bucket, moon_phase_fraction, market_volatility_proxy

# Engines & UI
from engine.meta_selector import meta_compose, improve_picks
from engine.ev_mode import adjust_for_ev
try:
    from ui.intentions import render_intention_ui as _render_intention_ui
except Exception:
    _render_intention_ui = None
from visuals.timeline_viz import render_white_surface
from utilities import jackpots as jp

ROOT = Path("."); DATA = Path("Data")
_rerun = getattr(st, "rerun", getattr(st, "experimental_rerun", None))


# ---------------- Page header ----------------
st.set_page_config(
    page_title="AstroLotto",
    page_icon="🎱",
    layout="wide"
)

# ---------------- Header ----------------
st.title("AstroLotto")
st.caption("Predict lottery numbers using history, per-ball models, oracle signals (moon / space / markets), quantum blending, hot/cold learning, and EV-aware de-popularization.")

# ---------------- Sidebar (initial toggles) ----------------
st.sidebar.header("Modules")
opt_oracle      = st.sidebar.checkbox("Oracle influence", True)
opt_quantum     = st.sidebar.checkbox("Quantum mode", True)
opt_archetype   = st.sidebar.checkbox("Archetypal weighting", True)
opt_retro       = st.sidebar.checkbox("Retrocausal learning", True)
opt_per_ball    = st.sidebar.checkbox("Per-ball learning (simple)", True)
opt_per_ball_ml = st.sidebar.checkbox("Per-ball ML (scikit-learn)", True)
opt_sacred      = st.sidebar.checkbox("Sacred geometry", True)
opt_ev_mode     = st.sidebar.checkbox("EV-aware unpopular-combo mode", True)
opt_viz         = st.sidebar.checkbox("Show probability surface", True)
opt_mc          = st.sidebar.checkbox("Use Monte Carlo synthesis", True)

# Intention toggle
opt_intention   = st.sidebar.checkbox("Enable intention UI (optional)", False)

# Quantum controls
st.sidebar.subheader("Quantum controls")
quantum_universes = st.sidebar.slider("Universes", 256, 4096, 1024, 256, disabled=not opt_quantum)
decoherence       = st.sidebar.slider("Decoherence", 0.00, 0.80, 0.55, 0.01, disabled=not opt_quantum)
observer_bias     = st.sidebar.slider("Observer bias", 0.00, 0.50, 0.20, 0.01, disabled=not opt_quantum)
use_qrng_flag     = st.sidebar.checkbox("Use QRNG for seeding", False, disabled=not opt_quantum)

# Consensus / shortlist
st.sidebar.subheader("Consensus & shortlist")
ensembles         = st.sidebar.slider("Worldline ensembles", 1, 21, 11, 1)
shortlist_k       = st.sidebar.slider("Shortlist size (top-K)", 0, 40, 22, 1)
diversity_min     = st.sidebar.slider("Min difference between sets (whites)", 0, 6, 2, 1)
min_unique_sp     = st.sidebar.slider("Min unique specials among sets", 0, 3, 2, 1)
candidate_pool    = st.sidebar.slider("Candidate pool (MC samples)", 50, 2000, 400, 50)
explore_temp      = st.sidebar.slider("Exploration temperature", 0.0, 1.0, 0.20, 0.05, help="Higher = more variety (Gumbel noise).")
mc_trials         = st.sidebar.slider("MC trials (extra sampling)", 0, 10000, 3000, 500, help="Additional simulations to learn combo frequencies.")
hc_alpha          = st.sidebar.slider("Hot/Cold influence", 0.0, 1.0, 0.30, 0.05, help="Blend of base model vs live hot/cold stats.")
hc_sharp          = st.sidebar.slider("Hot/Cold sharpness", 0.6, 1.6, 1.0, 0.1, help=">1 sharpens hot, <1 flattens.")

# Oracle detail toggles
st.sidebar.header("Oracle (details)")
oracle_use_moon    = st.sidebar.checkbox("Moon 🌕", True, disabled=not opt_oracle)
oracle_use_markets = st.sidebar.checkbox("Markets 📈", True, disabled=not opt_oracle)
oracle_use_space   = st.sidebar.checkbox("Space weather 🌋", True, disabled=not opt_oracle)
oracle_use_weird   = st.sidebar.checkbox("Planetary alignments 🪐", True, disabled=not opt_oracle)
oracle_gain        = st.sidebar.slider("Oracle gain (×)", 0.0, 5.0, 1.7, 0.1, disabled=not opt_oracle)

# --- Temporal helper (Kozyrev) ---
st.sidebar.header("Temporal helper")
opt_temporal = st.sidebar.checkbox("Enable temporal correction (Kozyrev)", False)

temporal_kappa    = st.sidebar.number_input("κ (s/J)", value=0.0, step=1e15, format="%.6e")
temporal_dt_ref   = st.sidebar.number_input("Δt₀ (ref sec)", value=86400.0, step=3600.0)
temporal_dt_win   = st.sidebar.number_input("Δt (window sec)", value=86400.0, step=3600.0)
temporal_eps_days = st.sidebar.number_input("ε (finite-diff days)", value=1.0, min_value=0.01, step=0.25)
controls_temporal = TemporalControls(
    enabled=bool(opt_temporal),
    kappa=float(temporal_kappa),
    dt_ref=float(temporal_dt_ref),
    dt_window=float(temporal_dt_win),
    eps_days=float(temporal_eps_days),
)
controls_temporal = TemporalControls(
    enabled=bool(opt_temporal),
    kappa=float(temporal_kappa),
    dt_ref=float(temporal_dt_ref),
    dt_window=float(temporal_dt_win),
    eps_days=float(temporal_eps_days),
)
oracle_sign        = st.sidebar.selectbox("Zodiac (optional)",
    ["", "aries","taurus","gemini","cancer","leo","virgo","libra","scorpio","sagittarius","capricorn","aquarius","pisces"],
    index=0, disabled=not opt_oracle)

# [autotune moved to page]
st.sidebar.subheader("Autotune κ (moved)")
al_logs_csv = st.sidebar.text_input("Logs CSV", value="Data/temporal_logs.csv")
al_results_csv = st.sidebar.text_input("Results CSV", value="Data/draw_results.csv")
al_kmin = st.sidebar.number_input("κ min", value=-5e16, format="%.3e")
al_kmax = st.sidebar.number_input("κ max", value= 5e16, format="%.3e")
al_ksteps = st.sidebar.number_input("Steps", min_value=3, value=41, step=2)
col_a1, col_a2 = st.sidebar.columns(2)
with col_a1:
    btn_run_autotune = st.button("Run autotune")
with col_a2:
    btn_reload_cfg = st.button("Reload config")

best_kappa_found = None
if btn_run_autotune:
    try:
        from temporal_autotune import tune_kappa_astrolotto
        res = tune_kappa_astrolotto(
            logs_csv=al_logs_csv,
            results_csv=al_results_csv,
            kappa_min=float(al_kmin),
            kappa_max=float(al_kmax),
            kappa_steps=int(al_ksteps),
            objective="mass_on_winners"
        )
        best_kappa_found = float(res.get("kappa", 0.0))
        st.sidebar.success(f"Best κ ≈ {best_kappa_found:.3e}")
        # Offer to save
        if st.sidebar.button("Save best κ to config"):
            meta = {"objective": "mass_on_winners", "objective_value": float(res.get("objective", 0.0)),
                    "scan": {"kappa_min": float(al_kmin), "kappa_max": float(al_kmax), "kappa_steps": int(al_ksteps)}}
            ok = _save_al_kappa_config(best_kappa_found, meta=meta)
            if ok:
                st.sidebar.info("Saved to extras/al_config.json")
            else:
                st.sidebar.error("Failed to save config.")
    except Exception as e:
        st.sidebar.error(f"Autotune failed: {e}")

if btn_reload_cfg:
    try:
        from programs.utilities.config import load_user_config as _load_cfg  # type: ignore
    except Exception:
        try:
            from utilities.config import load_user_config as _load_cfg  # type: ignore
        except Exception:
            _load_cfg = None  # type: ignore
    if _load_cfg:
        st.session_state['user_cfg'] = _load_cfg()  # type: ignore
        st.sidebar.success('Reloaded config into session.')
    else:
        st.sidebar.warning('Config module not available.')

# --- Immediate apply best κ ---
if best_kappa_found is not None and st.sidebar.button("Use best κ now"):
    st.session_state["temporal_kappa_default"] = float(best_kappa_found)
    temporal_kappa = float(best_kappa_found)
    st.sidebar.success(f"Applied κ = {best_kappa_found:.3e} for this session")


    try:
        new_default = _load_al_kappa_default()
        # Update the number_input default by writing into session_state, if present
        st.session_state["temporal_kappa_default"] = float(new_default)
        st.sidebar.info(f"Reloaded κ default: {new_default:.3e}")
    except Exception as e:
        st.sidebar.error(f"Reload failed: {e}")



# Training
st.sidebar.header("Training")
do_train_all   = st.sidebar.button("Train all games (per-ball ML)")

# Optional intention UI
if opt_intention and _render_intention_ui:
    _render_intention_ui()
else:
    st.session_state["intention_text"] = ""

# ---------------- Game selection & data ----------------
games = ["powerball","megamillions","cash5","pick3","luckyforlife","colorado_lottery"]
game = st.selectbox("Game", games, index=0)

cache_map = {"powerball": "cached_powerball_data.csv", "megamillions": "cached_megamillions_data.csv",
             "cash5": "cached_cash5_data.csv", "pick3": "cached_pick3_data.csv",
             "luckyforlife": "cached_luckyforlife_data.csv", "colorado_lottery": "cached_colorado_lottery_data.csv"}

def _rules_for(g: str) -> Dict[str,Any]:
    key = g if g in GAME_RULES else g.replace(" ","").lower()
    return GAME_RULES.get(key, {"white_max":70, "white_count":5, "special_max":None, "special_name":""})

def _special_max_from_rules(rules: Dict[str,Any]) -> Optional[int]:
    val = rules.get("special_max", None)
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return int(val)
    except Exception:
        return None

rules = _rules_for(game)
white_max = int(rules.get("white_max", 70))
white_count = int(rules.get("white_count", 5))
special_max = _special_max_from_rules(rules)
white_min = 0 if game == "pick3" else 1
diversity_min = int(max(0, min(diversity_min, white_count)))
min_unique_sp = int(max(0, min(min_unique_sp, 3)))

cache_csv = DATA / cache_map.get(game, "")
df = pd.read_csv(cache_csv) if cache_csv.exists() else pd.DataFrame()
base = compute_number_probs(df, game)

# ---- column alias helpers (for hot/cold & robustness) ----
def ALT_WHITE(i: int):
    return [f"n{i}", f"N{i}", f"w{i}", f"W{i}", f"white{i}", f"White{i}", f"num{i}", f"Num{i}", f"ball{i}", f"Ball{i}", f"d{i}", f"D{i}"]

def _find_col(df: pd.DataFrame, names) -> str | None:
    cols = set(df.columns)
    for n in names:
        if n in cols:
            return n
    norm = {str(c).strip().lower().replace(' ', '').replace('_',''): c for c in df.columns}
    for n in names:
        nn = str(n).strip().lower().replace(' ', '').replace('_','')
        if nn in norm:
            return norm[nn]
    return None

# ---------------- Oracle mods ----------------
def _scale_score_mult(obj, gain: float):
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return 1.0 + (float(obj) - 1.0) * float(gain)
    if isinstance(obj, dict):
        return {k: _scale_score_mult(v, gain) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_scale_score_mult(x, gain) for x in obj)
    return obj

def compute_oracle_mods() -> Dict[str,Any]:
    if not opt_oracle:
        return {"score_mult": {}, "chaos": 0.0, "parts": {}}
    settings = OracleSettings(
        use_moon=bool(oracle_use_moon),
        use_markets=bool(oracle_use_markets),
        use_space=bool(oracle_use_space),
        use_weird=bool(oracle_use_weird),
        user_sign=str(oracle_sign or ""),
    )
    mods = compute_oracle(dt.date.today(), white_min, white_max, settings)
    # Scale the multipliers and chaos by oracle_gain
    scaled = dict(mods)
    scaled["score_mult"] = _scale_score_mult(mods.get("score_mult", {}), oracle_gain)
    scaled["chaos"] = float(mods.get("chaos", 0.0)) * float(oracle_gain)
    # For display, scale parts but clamp at 1.0
    parts = dict(mods.get("parts", {}))
    for k, v in parts.items():
        try:
            parts[k] = min(1.0, float(v) * float(oracle_gain))
        except Exception as _e:
            print(\"Temporal logging failed:\", _e)
    scaled["parts"] = parts
    return scaled

oracle_mods = compute_oracle_mods()
oracle_mult = oracle_mods.get("score_mult") or {}
oracle_chaos = float(oracle_mods.get("chaos", 0.0))

# ---------------- Helpers for probability arrays ----------------
def _num_weights_array(w) -> np.ndarray:
    # array or dict -> dense array [0..white_max]
    try:
        arr = np.asarray(w).astype(float)
        if arr.ndim == 1 and len(arr) >= (white_max+1):
            return arr
    except Exception:
        pass
    try:
        arr = np.zeros(white_max+1, dtype=float)
        for i in range(white_max+1):
            arr[i] = float(w.get(i, 0.0))
        return arr
    except Exception:
        pass
    arr = np.ones(white_max+1, dtype=float)
    arr[0] = 0.0  # never pick 0 for non-pick3
    return arr

def _special_weights_array(s, special_max: Optional[int]) -> Optional[np.ndarray]:
    if not special_max:
        return None
    try:
        arr = np.asarray(s).astype(float)
        if arr.ndim == 1 and len(arr) >= (special_max+1):
            return arr
    except Exception:
        pass
    try:
        arr = np.zeros(special_max+1, dtype=float)
        for i in range(special_max+1):
            arr[i] = float(s.get(i, 0.0))
        return arr
    except Exception:
        return None

# ---------------- Hot/Cold learning ----------------
def _hotcold_vector(df: pd.DataFrame) -> np.ndarray:
    counts = np.zeros(white_max+1, dtype=float)
    if df is None or df.empty:
        return counts
    found = False
    for i in range(1, white_count+1):
        col = _find_col(df, ALT_WHITE(i))
        if col and (col in df.columns):
            found = True
            vals = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
            for v in vals:
                if white_min <= v <= white_max:
                    counts[v] += 1
    if not found or counts.sum() == 0:
        return counts
    # normalize
    counts[0] = 0.0  # don't use 0 for non-pick3'
    total = counts.sum()
    if total > 0:
        counts = counts / total
    return counts

def _blend_hotcold(W_base: np.ndarray, hc: np.ndarray, alpha: float, sharp: float) -> np.ndarray:
    if alpha <= 0 or hc.sum() <= 0:
        return W_base
    # sharpen/flatten
    hc2 = np.power(np.clip(hc, 1e-12, None), float(sharp))
    hc2 = hc2 / hc2.sum()
    out = (1.0 - alpha) * W_base + alpha * hc2
    s = out.sum()
    if s > 0:
        out = out / s
    return out


def _get_weights_for_epoch_dateaware(epoch_s: float) -> list[float]:
    """Recompute white-ball weight vector W for the given epoch (seconds)."""
    date_obj = dt.datetime.utcfromtimestamp(float(epoch_s)).date()
    mods = compute_oracle_mods()
    mult = mods.get('score_mult') or {}
    chaos = float(mods.get('chaos', 0.0))
    w_comp, s_comp, _ = meta_compose(
        game=game, df=df, date=date_obj,
        user=dict(name=st.session_state.get('user_name'),
                  birthdate=st.session_state.get('user_birthdate'),
                  lucky_whites=st.session_state.get('lucky_whites', []),
                  lucky_specials=st.session_state.get('lucky_specials', [])),
        opts=dict(
            base=base,
            use_per_ball=bool(opt_per_ball),
            per_ball_ml=[],  # keep time-variance from Oracle/controls
            use_sacred=bool(opt_sacred),
            use_archetype=bool(opt_archetype),
            use_quantum=bool(opt_quantum),
            universes=int(quantum_universes), decoherence=float(decoherence), observer_bias=float(observer_bias),
            use_qrng=bool(use_qrng_flag),
            use_retro=bool(opt_retro),
            retro_horizon=120, retro_memory=0.35,
            oracle_score_mult=mult,
            oracle_chaos=chaos,
            intention_text=(st.session_state.get('intention_text') or '') if opt_intention else '',
            intention_strength=0.01 if opt_intention else 0.0,
            ensembles=int(ensembles),
            seed=0,
        )
    )
    W_local = _weights_array(w_comp, white_max)
    s = W_local.sum()
    if s > 0:
        W_local = W_local / s
    return W_local.tolist()
def _get_special_for_epoch_dateaware(epoch_s: float) -> list[float]:
    """
    Recompute special-ball weight vector for the given epoch (seconds).
    """
    date_obj = dt.datetime.utcfromtimestamp(float(epoch_s)).date()
    mods = compute_oracle_mods()
    mult = mods.get("score_mult") or {}
    chaos = float(mods.get("chaos", 0.0))
    w_comp, s_comp, _ = meta_compose(
        game=game, df=df, date=date_obj,
        user=dict(name=st.session_state.get("user_name"),
                  birthdate=st.session_state.get("user_birthdate"),
                  lucky_whites=st.session_state.get("lucky_whites", []),
                  lucky_specials=st.session_state.get("lucky_specials", [])),
        opts=dict(
            base=base,
            use_per_ball=bool(opt_per_ball),
            per_ball_ml=[],
            use_sacred=bool(opt_sacred),
            use_archetype=bool(opt_archetype),
            use_quantum=bool(opt_quantum),
            universes=int(quantum_universes), decoherence=float(decoherence), observer_bias=float(observer_bias),
            use_qrng=bool(use_qrng_flag),
            use_retro=bool(opt_retro),
            retro_horizon=120, retro_memory=0.35,
            oracle_score_mult=mult,
            oracle_chaos=chaos,
            intention_text=(st.session_state.get("intention_text") or "") if opt_intention else "",
            intention_strength=0.01 if opt_intention else 0.0,
            ensembles=int(ensembles),
            seed=0,
        )
    )
    Sp_local = _special_weights_array(s_comp, special_max)
    s = Sp_local.sum()
    if s > 0:
        Sp_local = Sp_local / s
    return Sp_local.tolist()
def _get_special_weights_for_epoch_dateaware(epoch_s: float) -> list[float]:
    """
    Recompute special-ball weight vector Sp for the given epoch (seconds).
    """
    date_obj = dt.datetime.utcfromtimestamp(float(epoch_s)).date()
    mods = compute_oracle_mods()
    mult = mods.get("score_mult") or {}
    chaos = float(mods.get("chaos", 0.0))
    # Compose again
    w_comp, s_comp, _ = meta_compose(
        game=game, df=df, date=date_obj,
        user=dict(name=st.session_state.get("user_name"),
                  birthdate=st.session_state.get("user_birthdate"),
                  lucky_whites=st.session_state.get("lucky_whites", []),
                  lucky_specials=st.session_state.get("lucky_specials", [])),
        opts=dict(
            base=base,
            use_per_ball=bool(opt_per_ball),
            per_ball_ml=[],
            use_sacred=bool(opt_sacred),
            use_archetype=bool(opt_archetype),
            use_quantum=bool(opt_quantum),
            universes=int(quantum_universes), decoherence=float(decoherence), observer_bias=float(observer_bias),
            use_qrng=bool(use_qrng_flag),
            use_retro=bool(opt_retro),
            retro_horizon=120, retro_memory=0.35,
            oracle_score_mult=mult,
            oracle_chaos=chaos,
            intention_text=(st.session_state.get("intention_text") or "") if opt_intention else "",
            intention_strength=0.01 if opt_intention else 0.0,
            ensembles=int(ensembles),
            seed=0,
        )
    )
    Sp_local = _special_weights_array(s_comp) if s_comp is not None else None
    if Sp_local is not None:
        ssum = Sp_local.sum()
        if ssum > 0:
            Sp_local = Sp_local / ssum
        return Sp_local.tolist()
    return []

    """
    Recompute white-ball weight vector W for the given epoch (seconds), using the
    same pipeline as baseline but with Oracle date bound to that epoch's UTC date.
    """
    date_obj = dt.datetime.utcfromtimestamp(float(epoch_s)).date()
    # Compose using existing knobs/state in scope
    mods = compute_oracle_mods()  # sidebar-driven; gain and parts already applied
    mult = mods.get("score_mult") or {}
    chaos = float(mods.get("chaos", 0.0))
    # Build composition
    w_comp, s_comp, _ = meta_compose(
        game=game, df=df, date=date_obj,
        user=dict(name=st.session_state.get("user_name"),
                  birthdate=st.session_state.get("user_birthdate"),
                  lucky_whites=st.session_state.get("lucky_whites", []),
                  lucky_specials=st.session_state.get("lucky_specials", [])),
        opts=dict(
            base=base,
            use_per_ball=bool(opt_per_ball),
            per_ball_ml=[],  # keep time-variance from Oracle/controls
            use_sacred=bool(opt_sacred),
            use_archetype=bool(opt_archetype),
            use_quantum=bool(opt_quantum),
            universes=int(quantum_universes), decoherence=float(decoherence), observer_bias=float(observer_bias),
            use_qrng=bool(use_qrng_flag),
            use_retro=bool(opt_retro),
            retro_horizon=120, retro_memory=0.35,
            oracle_score_mult=mult,
            oracle_chaos=chaos,
            intention_text=(st.session_state.get("intention_text") or "") if opt_intention else "",
            intention_strength=0.01 if opt_intention else 0.0,
            ensembles=int(ensembles),
            seed=0,
        )
    )
    W_base_local = _num_weights_array(w_comp)
    # Hot/Cold blend (same as baseline)
    if game != "pick3" and hc_alpha > 0:
        HC = _hotcold_vector(df)
        W_local = _blend_hotcold(W_base_local, HC, alpha=float(hc_alpha), sharp=float(hc_sharp))
    else:
        W_local = W_base_local
    s = W_local.sum()
    if s > 0:
        W_local = W_local / s
    return W_local.tolist()


def _weights_at_epoch(t_epoch: float) -> np.ndarray:
    """Return white-ball weights W at a given epoch (seconds), reusing existing pipeline with Oracle date tied to epoch."""
    date_obj = dt.datetime.utcfromtimestamp(float(t_epoch)).date()
    mods = compute_oracle_mods()  # uses current sidebar settings
    # If your compute_oracle_mods uses today's date, we may need a date-aware variant.
    # For now we assume other components (meta_compose) take 'date' parameter where needed.

    # Build base weight arrays from current context
    # We reuse local variables from the calling scope, so this will be used inside predict() where w/s are built.

    # NOTE: This placeholder simply returns the most recent W_base computed at runtime.
    # The true time-aware version should re-run your meta_compose() with date=date_obj.
    # To keep this patch minimal and safe, we will compute sensitivity by perturbing draw date at selection time instead.

    # Return last computed W as fallback (will be overwritten in apply step).
    return W_base

def _vector_fd_sensitivity(model_fn, eps_sec: float):
    def _s(t_next: float, state: Dict[str,Any], ctx: Dict[str,Any]):
        Wp = np.asarray(model_fn(t_next + eps_sec, state, ctx), dtype=float)
        Wm = np.asarray(model_fn(t_next - eps_sec, state, ctx), dtype=float)
        if Wp.shape != Wm.shape:
            raise ValueError("FD sensitivity: shape mismatch.")
        return ((Wp - Wm) / (2.0 * eps_sec)).tolist()
    return _s
# ---------------- Robust local frequency fallback ----------------
def _local_frequency_picks(df: pd.DataFrame, n_sets: int) -> List[Dict[str,Any]]:
    rng = np.random.default_rng()
    picks = []
    if df is None or df.empty:
        for _ in range(n_sets):
            if game == "pick3":
                picks.append({"white": list(rng.integers(low=0, high=10, size=3)), "special": None, "notes": ""})
            else:
                choices = rng.choice(np.arange(white_min, white_max+1), size=white_count, replace=False)
                picks.append({"white": sorted(map(int, choices)), "special": None, "notes": ""})
        return picks

    counts = np.zeros(white_max+1, dtype=int)
    for i in range(1, white_count+1):
        col = f"n{i}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
            for v in vals:
                if white_min <= v <= white_max:
                    counts[v] += 1

    order = np.argsort(counts)[::-1]
    top = [int(i) for i in order if white_min <= i <= white_max][:max(white_count*6, white_count+6)]
    for _ in range(n_sets):
        if game == "pick3":
            freqs = counts[white_min:white_max+1].astype(float) + 1.0
            freqs = freqs / freqs.sum()
            digits = rng.choice(np.arange(white_min, white_max+1), size=3, replace=True, p=freqs)
            picks.append({"white": list(map(int, digits)), "special": None, "notes": "local-freq"})
        else:
            pool = top[:max(white_count*4, white_count+6)]
            if len(pool) < white_count:
                pool = list(range(white_min, white_max+1))
            choice = sorted(rng.choice(pool, size=white_count, replace=False))
            sp = None
            if special_max:
                if "s1" in df.columns:
                    sc = np.zeros(special_max+1, dtype=int)
                    svals = pd.to_numeric(df["s1"], errors="coerce").dropna().astype(int)
                    for v in svals:
                        if 1 <= v <= special_max: sc[v] += 1
                    sp = int(np.argmax(sc[1:]) + 1) if sc[1:].sum()>0 else int(rng.integers(1, special_max+1))
                else:
                    sp = int(rng.integers(1, special_max+1))
            picks.append({"white": choice, "special": sp, "notes": "local-freq"})
    return picks

def _call_fallback_predict(n_sets: int) -> List[Dict[str,Any]]:
    try:
        sig = inspect.signature(predict_frequency_fallback)
        params = list(sig.parameters.keys())
        if "model" in params and "n_picks" in params:
            raw = predict_frequency_fallback(df, game, None, n_picks=n_sets)
        elif "n_picks" in params:
            raw = predict_frequency_fallback(df, game, n_picks=n_sets)
        else:
            raw = predict_frequency_fallback(df, game)
            raw = raw[:n_sets] if isinstance(raw, list) else [raw]
        picks = []
        for r in raw:
            if isinstance(r, dict):
                picks.append({"white": r.get("white", []), "special": r.get("special"), "notes": r.get("notes","")})
            elif isinstance(r, (list, tuple)):
                picks.append({"white": list(r), "special": None, "notes": ""})
        if not picks or any(not p.get("white") for p in picks):
            return _local_frequency_picks(df, n_sets)
        return picks
    except Exception:
        return _local_frequency_picks(df, n_sets)

# ---------------- Candidate generation & selection ----------------
def _gumbel_noise(size: int, scale: float) -> np.ndarray:
    if scale <= 0:
        return np.zeros(size, dtype=float)
    U = np.clip(np.random.rand(size), 1e-12, 1-1e-12)
    return -np.log(-np.log(U)) * float(scale)

def _score_set(whites: List[int], sp: Optional[int], W: np.ndarray, Sp: Optional[np.ndarray]) -> float:
    eps = 1e-12
    score = 0.0
    for n in whites:
        if 0 <= n < len(W):
            score += math.log(max(W[n], eps))
    if Sp is not None and sp is not None and 0 <= sp < len(Sp):
        score += 0.6 * math.log(max(Sp[sp], eps))  # smaller contribution
    return score

def _sample_candidates(W: np.ndarray, Sp: Optional[np.ndarray], n_cand: int, shortlist_k: int) -> List[Dict[str,Any]]:
    rng = np.random.default_rng()
    domain = np.arange(white_min, white_max+1)
    # shortlist pool
    if shortlist_k and shortlist_k > 0:
        order = np.argsort(W)[::-1]
        pool = [int(i) for i in order if white_min <= i <= white_max][:int(shortlist_k)]
        if len(pool) < white_count:
            pool = [int(i) for i in order if white_min <= i <= white_max][:max(white_count+6, white_count*3)]
    else:
        pool = [int(i) for i in domain]

    Wp = np.array([max(W[i], 0.0) for i in pool], dtype=float)
    if Wp.sum() <= 0:
        Wp = None
    else:
        Wp = Wp / Wp.sum()

    cand = []
    for _ in range(int(n_cand)):
        whites = sorted(rng.choice(pool, size=white_count, replace=False, p=Wp))
        sp = None
        if special_max and Sp is None:
            sp = int(np.random.default_rng().integers(1, special_max+1))
        if Sp is not None and special_max:
            Sp1 = np.copy(Sp)
            Sp1[0] = 0.0 if game != "pick3" else Sp1[0]
            if Sp1.sum() > 0:
                Sp1 = Sp1 / Sp1.sum()
                sp = int(rng.choice(np.arange(len(Sp1)), p=Sp1))
                if sp == 0 and game != "pick3":
                    sp = 1
            else:
                sp = int(rng.integers(1, special_max+1))
        cand.append({"white": whites, "special": sp})
    return cand

def _monte_carlo_top(W: np.ndarray, Sp: Optional[np.ndarray], trials: int, shortlist_k: int, topN: int) -> List[Dict[str,Any]]:
    if trials <= 0:
        return []
    rng = np.random.default_rng()
    domain = np.arange(white_min, white_max+1)

    # Pool as in _sample_candidates
    if shortlist_k and shortlist_k > 0:
        order = np.argsort(W)[::-1]
        pool = [int(i) for i in order if white_min <= i <= white_max][:int(shortlist_k)]
        if len(pool) < white_count:
            pool = [int(i) for i in order if white_min <= i <= white_max][:max(white_count+6, white_count*3)]
    else:
        pool = [int(i) for i in domain]

    Wp = np.array([max(W[i], 0.0) for i in pool], dtype=float)
    Wp = (Wp / Wp.sum()) if Wp.sum() > 0 else None

    counts: Dict[Tuple[int,...], int] = {}
    for _ in range(int(trials)):
        whites = tuple(sorted(rng.choice(pool, size=white_count, replace=False, p=Wp)))
        counts[whites] = counts.get(whites, 0) + 1
    # Take top combos by frequency
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:max(3, topN)]
    out = [{"white": list(k), "special": None} for k, _ in top]
    return out

def _select_diverse_top(cand: List[Dict[str,Any]], n_sets: int, W: np.ndarray, Sp: Optional[np.ndarray],
                        min_diff: int, min_unique_sp: int, explore_temp: float) -> List[Dict[str,Any]]:
    # Score candidates
    scores = np.array([_score_set(c["white"], c.get("special"), W, Sp) for c in cand], dtype=float)
    scores = scores + _gumbel_noise(len(scores), explore_temp)
    order = np.argsort(scores)[::-1]

    selected: List[Dict[str,Any]] = []
    used_specials: List[int] = []

    def ok_diversity(whites):
        for s in selected:
            diff = white_count - len(set(whites) & set(s["white"]))
            if diff < min_diff:
                return False
        return True

    for idx in order:
        c = cand[idx]
        whites = c["white"]; sp = c.get("special")
        if not ok_diversity(whites):
            continue
        # prefer new specials until we hit min_unique_sp
        if special_max and sp is not None and min_unique_sp > 0:
            if len(set(used_specials)) < min_unique_sp and sp in used_specials:
                continue
        selected.append(c)
        if special_max and sp is not None:
            used_specials.append(sp)
        if len(selected) >= n_sets:
            break

    # If not enough sets, relax special uniqueness to fill to n_sets (still keeping min_diff)
    if len(selected) < n_sets:
        for idx in order:
            if len(selected) >= n_sets: break
            c = cand[idx]
            whites = c["white"]
            if ok_diversity(whites) and c not in selected:
                selected.append(c)

    return selected[:n_sets]


def _choose_special(Sp, special_max: int) -> int:
    rng = np.random.default_rng()
    if Sp is not None and isinstance(Sp, np.ndarray) and Sp.size >= (special_max+1):
        probs = Sp.copy().astype(float)
        if len(probs) > 0:
            # index 0 is invalid for non-pick3
            if len(probs) > 0 and probs.sum() > 0:
                probs[0] = 0.0
                s = probs.sum()
                if s > 0:
                    probs = probs / s
                    idx = int(rng.choice(np.arange(len(probs)), p=probs))
                    if idx == 0:
                        idx = 1
                    return idx
    return int(rng.integers(1, special_max+1))

def _ensure_specials(picks, Sp, special_max: int, min_unique_sp: int):
    # Assign missing specials
    for p in picks:
        if p.get("special") in (None, "", 0) and special_max:
            p["special"] = _choose_special(Sp, special_max)
    # Enforce minimum uniqueness across sets (best-effort)
    if not special_max or min_unique_sp <= 0 or len(picks) <= 1:
        return picks
    used = [p.get("special") for p in picks if p.get("special") is not None]
    uniq = set(used)
    need = max(0, int(min_unique_sp) - len(uniq))
    if need <= 0:
        return picks
    # Try to introduce new specials by reassigning duplicates
    all_vals = set(range(1, special_max+1))
    candidates = list(all_vals - uniq)
    rng = np.random.default_rng()
    i = 0
    for p in picks:
        if need <= 0 or not candidates:
            break
        s = p.get("special")
        # change only duplicates
        if used.count(s) > 1:
            new_s = candidates.pop(0)
            p["special"] = int(new_s)
            need -= 1
    # If still need, randomly mutate remaining
    while need > 0 and candidates:
        j = rng.integers(0, len(picks))
        picks[j]["special"] = int(candidates.pop(0))
        need -= 1
    return picks

# ---------------- Prediction wrapper ----------------
def _predict(n_sets: int):
    # Start from baseline heuristic picks
    picks = _call_fallback_predict(n_sets)

    # Optional per-ball ML probabilities
    per_ball_ml_probs = []
    if opt_per_ball_ml and not df.empty:
        try:
            model_pack = train_per_ball_ml(game, df, neg_per_pos=4)
            per_ball_ml_probs = predict_per_ball_ml(df, model_pack)
        except Exception as e:
            st.info(f"Per-ball ML unavailable: {e}")
            per_ball_ml_probs = []

    # Meta blending
    w, s, tarot = meta_compose(
        game=game, df=df, date=dt.date.today(),
        user=dict(name=st.session_state.get("user_name"), birthdate=st.session_state.get("user_birthdate"),
                  lucky_whites=st.session_state.get("lucky_whites", []), lucky_specials=st.session_state.get("lucky_specials", [])),
        opts=dict(
            base=base,
            use_per_ball=bool(opt_per_ball),
            per_ball_ml=per_ball_ml_probs,
            use_sacred=bool(opt_sacred),
            use_archetype=bool(opt_archetype),
            use_quantum=bool(opt_quantum),
            universes=int(quantum_universes), decoherence=float(decoherence), observer_bias=float(observer_bias),
            use_qrng=bool(use_qrng_flag),
            use_retro=bool(opt_retro),
            retro_horizon=120, retro_memory=0.35,
            oracle_score_mult=oracle_mult,
            oracle_chaos=oracle_chaos,
            intention_text=(st.session_state.get("intention_text") or "") if opt_intention else "",
            intention_strength=0.01 if opt_intention else 0.0,
            ensembles=int(ensembles),
            seed=0,  # meta_selector expects int
        )
    )

    # Improve baseline picks with shortlist
    picks = improve_picks(picks, w, s, shortlist_k=int(shortlist_k))

    # EV-aware tweak (de-popularize)
    if opt_ev_mode and game != "pick3":
        picks = adjust_for_ev(picks, w, white_max=white_max, max_drop_pct=0.02)

    # Build dense arrays
    W_base = _num_weights_array(w)
    Sp = _special_weights_array(s, special_max)
    W_base_copy_for_log = None
    Sp_base_copy_for_log = None

    # Blend in Hot/Cold learning
    if game != "pick3" and hc_alpha > 0:
        HC = _hotcold_vector(df)
        W = _blend_hotcold(W_base, HC, alpha=float(hc_alpha), sharp=float(hc_sharp))
    else:
        W = W_base
    # copies for logging
    try:
        W_base_copy_for_log = W.copy()
        Sp_base_copy_for_log = Sp.copy() if Sp is not None else None
    except Exception:
        W_base_copy_for_log = None
        Sp_base_copy_for_log = None

    
    # --- Temporal correction for white-ball weights (date-aware) ---
    try:
        if 'controls_temporal' in globals() and controls_temporal.enabled and controls_temporal.kappa != 0.0 and game != "pick3":
            next_draw_epoch = _next_draw_epoch_seconds()
            res_temporal = apply_temporal_to_weights(
                get_weights_for_epoch=_get_weights_for_epoch_dateaware,
                controls=controls_temporal,
                next_draw_epoch=next_draw_epoch,
            )
        diag_w_for_log = res_temporal.get('diagnostics', {})
        import numpy as _np
        W = _np.asarray(res_temporal['W_final'], dtype=float)
    except Exception as _e:
        pass  # fail-safe

    
    # --- Temporal correction for special-ball weights (date-aware) ---
    try:
        if 'controls_temporal' in globals() and controls_temporal.enabled and controls_temporal.kappa != 0.0 and special_max and Sp is not None:
            next_draw_epoch = _next_draw_epoch_seconds()
            res_temporal_sp = apply_temporal_to_weights(
                get_weights_for_epoch=_get_special_weights_for_epoch_dateaware,
                controls=controls_temporal,
                next_draw_epoch=next_draw_epoch,
            )
            import numpy as _np
            Sp = _np.asarray(res_temporal_sp["W_final"], dtype=float)
    except Exception as _e:
        pass  # fail-safe

# Generate candidates

    if n_sets > 1 and game != "pick3":
        cand = _sample_candidates(W, Sp, n_cand=candidate_pool, shortlist_k=int(shortlist_k))
        # Add MC-derived top combos
        if opt_mc and mc_trials > 0:
            top_mc = _monte_carlo_top(W, Sp, trials=int(mc_trials), shortlist_k=int(shortlist_k), topN=max(3, n_sets*2))
            # Ensure specials for MC top using Sp
            if Sp is not None and special_max:
                rng = np.random.default_rng()
                Sp1 = Sp.copy(); Sp1[0] = 0.0 if game != "pick3" else Sp1[0]
                if Sp1.sum() > 0: Sp1 = Sp1/Sp1.sum()
                for c in top_mc:
                    if c.get("special") is None:
                        if Sp1.sum() > 0:
                            c["special"] = int(rng.choice(np.arange(len(Sp1)), p=Sp1))
                            if c["special"] == 0 and game != "pick3":
                                c["special"] = 1
                        else:
                            c["special"] = int(rng.integers(1, special_max+1))
            # Merge (dedupe by whites+special)
            seen = set()
            merged = []
            for c in (top_mc + cand):
                key = (tuple(c["white"]), c.get("special"))
                if key in seen: continue
                seen.add(key); merged.append(c)
            cand = merged

        # Select diverse top candidates
        picks = _select_diverse_top(cand, n_sets=n_sets, W=W, Sp=Sp,
                                    min_diff=int(diversity_min), min_unique_sp=int(min_unique_sp),
                                    explore_temp=float(explore_temp))
        # Ensure specials are present and meet min uniqueness
        if special_max:
            picks = _ensure_specials(picks, Sp, special_max=int(special_max), min_unique_sp=int(min_unique_sp))

    out = []
    for p in picks:
        whites_sorted = sorted([int(x) for x in p["white"]]) if game != "pick3" else [int(x) for x in p["white"]]
        sp = p.get("special")
        sp_val = None if (sp in ("", None)) else int(sp)
        out.append({"white": whites_sorted, "special": sp_val, "notes": str(p.get("notes",""))})
    
# ---- Safeguards: ensure names exist even if earlier steps failed ----
if 'out' not in locals():
    out = None
if 'W' not in locals():
    W = None
if 'Sp' not in locals():
    Sp = None

# ---- Temporal logging (for learning baseline) ----
try:
    next_draw_epoch_for_log = _next_draw_epoch_seconds()
    _log_temporal_run(
        game=game,
        next_draw_epoch=next_draw_epoch_for_log,
        controls=controls_temporal if 'controls_temporal' in globals() else None,
        diag_w=locals().get('diag_w_for_log'),
        diag_sp=locals().get('diag_sp_for_log'),
        W_base=(W_base_copy_for_log.tolist() if hasattr(W_base_copy_for_log,"tolist") else W_base_copy_for_log),
        W_final=(W.tolist() if hasattr(W,"tolist") else None),
        Sp_base=(Sp_base_copy_for_log.tolist() if (Sp_base_copy_for_log is not None and hasattr(Sp_base_copy_for_log,"tolist")) else Sp_base_copy_for_log),
        Sp_final=(Sp.tolist() if (Sp is not None and hasattr(Sp,"tolist")) else None),
        picks=out,
    )
except Exception:
    pass
out_last = (out, W, Sp, None)  # stored for viz; avoid top-level return on cloud


def _entropy(vec):
    import math
    s = float(sum(max(1e-18, float(x)) for x in vec))
    if s <= 0: return 0.0
    H = 0.0
    for x in vec:
        p = max(1e-18, float(x)) / s
        H -= p * math.log(p + 1e-18)
    return H

def _log_temporal_run(game: str,
                      next_draw_epoch: float,
                      controls,
                      diag_w: dict | None,
                      diag_sp: dict | None,
                      W_base: list[float] | None,
                      W_final: list[float] | None,
                      Sp_base: list[float] | None,
                      Sp_final: list[float] | None,
                      picks: list[dict] | None):
    """
    Append a row to Data/temporal_logs.csv capturing diagnostics for learning.
    """
    try:
        os.makedirs("Data", exist_ok=True)
        path = os.path.join("Data", "temporal_logs.csv")
        # Prepare row
        import time
        row = {
            "run_ts": int(time.time()),
            "game": str(game),
            "next_draw_epoch": float(next_draw_epoch),
            "kappa": float(getattr(controls, "kappa", 0.0)),
            "dt_ref": float(getattr(controls, "dt_ref", 0.0)),
            "dt_window": float(getattr(controls, "dt_window", 0.0)),
            "eps_days": float(getattr(controls, "eps_days", 0.0)),
        }
        # White diagnostics
        if diag_w:
            row.update({
                "Et_w": diag_w.get("Et"),
                "Et0_w": diag_w.get("Et0"),
                "dtK_w": diag_w.get("dt_K"),
                "entropy_W_base": _entropy(W_base or []),
                "entropy_W_final": _entropy(W_final or []),
            })
        else:
            row.update({"Et_w": None, "Et0_w": None, "dtK_w": None,
                        "entropy_W_base": _entropy(W_base or []),
                        "entropy_W_final": _entropy(W_final or [])})
        # Special diagnostics
        if diag_sp:
            row.update({
                "Et_sp": diag_sp.get("Et"),
                "Et0_sp": diag_sp.get("Et0"),
                "dtK_sp": diag_sp.get("dt_K"),
                "entropy_Sp_base": _entropy(Sp_base or []),
                "entropy_Sp_final": _entropy(Sp_final or []),
            })
        else:
            row.update({"Et_sp": None, "Et0_sp": None, "dtK_sp": None,
                        "entropy_Sp_base": _entropy(Sp_base or []),
                        "entropy_Sp_final": _entropy(Sp_final or [])})
        # Top pick (first set)
        if picks and len(picks) > 0:
            p0 = picks[0]
            row["top_pick_white"] = json.dumps(p0.get("white"))
            row["top_pick_special"] = p0.get("special")
        else:
            row["top_pick_white"] = None
            row["top_pick_special"] = None

        # Save distributions (optional, as JSON strings)
        row["W_base"] = json.dumps(W_base) if W_base is not None else None
        row["W_final"] = json.dumps(W_final) if W_final is not None else None
        row["Sp_base"] = json.dumps(Sp_base) if Sp_base is not None else None
        row["Sp_final"] = json.dumps(Sp_final) if Sp_final is not None else None

        # Write header if file is new
        write_header = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                w.writeheader()
            w.writerow(row)
    except Exception as e:
        # fail silently to avoid breaking UI
        pass


def _al_config_path():
    # default location inside project
    return os.path.join("extras", "al_config.json")

def _load_al_kappa_default(path=None, fallback=0.0):
    """Load default κ from autotuner config JSON, fallback if not found."""
    path = path or _al_config_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return float(json.load(f).get("kappa", fallback))
    except Exception:
        pass
    return float(fallback)

def _save_al_kappa_config(kappa: float, meta: dict | None = None, path=None) -> bool:
    """Persist κ and metadata to config JSON."""
    path = path or _al_config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import time
        payload = {"kappa": float(kappa), "updated_at": int(time.time())}
        if isinstance(meta, dict):
            payload.update(meta)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False

# ---------------- Helpers: presentation ----------------
def _format_plain_line(idx: int, p: Dict[str,Any]) -> str:
    if game == "pick3":
        return f"Pick {idx}: {p['white'][0]}-{p['white'][1]}-{p['white'][2]}"
    whites = sorted([int(x) for x in p.get('white', [])])
    if p.get("special") is not None:
        return f"Pick {idx}: {' '.join(map(str,whites))} | Special: {p['special']}"
    return f"Pick {idx}: {' '.join(map(str,whites))}"

def _hot_cold_panel():
    if df.empty:
        st.info("No history found for this game yet.")
        return

    counts = np.zeros(white_max+1, dtype=int)
    found_any = False
    for i in range(1, white_count+1):
        col = _find_col(df, ALT_WHITE(i))
        if col and (col in df.columns):
            found_any = True
            vals = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
            vals = vals[(vals>=white_min) & (vals<=white_max)].values
            for v in vals:
                counts[int(v)] += 1

    if not found_any or counts.sum() == 0:
        st.info("No frequency data available yet for hot/cold.")
        return

    order_hot = np.argsort(counts)[::-1]
    order_cold = np.argsort(counts)

    # Build hot list from highest counts that are >0
    hot_list = []
    for idx in order_hot:
        if idx < white_min or idx > white_max:
            continue
        c = int(counts[idx])
        if c <= 0:
            break
        hot_list.append((int(idx), c))
        if len(hot_list) >= min(10, white_max):
            break

    # Build cold list from lowest non-zero counts; if all zero, show smallest indices
    cold_list = []
    nonzero = [i for i in range(white_min, white_max+1) if counts[i] > 0]
    if nonzero:
        for idx in order_cold:
            if idx < white_min or idx > white_max:
                continue
            c = int(counts[idx])
            if c <= 0:
                continue
            cold_list.append((int(idx), c))
            if len(cold_list) >= min(10, white_max):
                break
    else:
        cold_list = [(i, 0) for i in range(white_min, min(white_min+10, white_max+1))]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 Hot (most frequent)")
        st.write(", ".join([f"{n} ({c})" for n,c in hot_list]))
    with c2:
        st.subheader("🧊 Cold (least frequent)")
        st.write(", ".join([f"{n} ({c})" for n,c in cold_list]))

def _next_draw_info():
    st.subheader("📅 Next draw & jackpot")
    schedules = {
        "powerball": dict(days=[0,2,5], hour=20, minute=59),
        "megamillions": dict(days=[1,4], hour=21, minute=0),
        "cash5": dict(days=list(range(7)), hour=19, minute=35),
        "pick3": dict(days=list(range(7)), hour=19, minute=35),
        "luckyforlife": dict(days=list(range(7)), hour=20, minute=38),
        "colorado_lottery": dict(days=list(range(7)), hour=19, minute=35),
    }
    now = dt.datetime.now()
    s = schedules.get(game, dict(days=list(range(7)), hour=20, minute=0))
    for i in range(8):
        cand = now + dt.timedelta(days=i)
        if cand.weekday() in s["days"]:
            draw_dt = cand.replace(hour=s["hour"], minute=s["minute"], second=0, microsecond=0)
            if draw_dt > now or i>0:
                break
    else:
        draw_dt = now

    def _norm(s): return s.strip().lower().replace(" ","").replace("_","").replace("-","")
    gk = _norm(game)
    jackpot_val = None
    if gk == _norm("powerball"):
        jackpot_val = jp.get_jackpot("powerball")
    elif gk == _norm("megamillions"):
        jackpot_val = jp.get_jackpot("megamillions")
    elif gk in (_norm("colorado_lottery"), _norm("colorado")):
        jackpot_val = jp.get_jackpot("colorado")
    jack_str = f"${jackpot_val:,}" if isinstance(jackpot_val, int) and jackpot_val>0 else "n/a"

    cols = st.columns(2)
    with cols[0]:
        st.metric("Next draw (est.)", draw_dt.strftime("%a %b %d, %I:%M %p"))
    with cols[1]:
        st.metric("Jackpot", jack_str)

# ---------------- Buttons (main) ----------------

def _next_draw_epoch_seconds() -> float:
    """Return next draw datetime as epoch seconds using the same schedule as _next_draw_info."""
    schedules = {
        "powerball": dict(days=[0,2,5], hour=20, minute=59),
        "megamillions": dict(days=[1,4], hour=21, minute=0),
        "cash5": dict(days=list(range(7)), hour=19, minute=35),
        "pick3": dict(days=list(range(7)), hour=19, minute=35),
        "luckyforlife": dict(days=list(range(7)), hour=20, minute=38),
        "colorado_lottery": dict(days=list(range(7)), hour=19, minute=35),
    }
    now = dt.datetime.now()
    s = schedules.get(game, dict(days=list(range(7)), hour=20, minute=0))
    for i in range(8):
        cand = now + dt.timedelta(days=i)
        if cand.weekday() in s["days"]:
            draw_dt = cand.replace(hour=s["hour"], minute=s["minute"], second=0, microsecond=0)
            if draw_dt > now or i > 0:
                return draw_dt.timestamp()
    return now.timestamp()

def _render_results(picks, W, Sp):
    st.subheader("Your numbers")
    for i, p in enumerate(picks, 1):
        line = _format_plain_line(i, p)
        badge = " 🟢" if "diversity" in (p.get("notes","").lower()) else ""
        st.markdown(f"**{line}{badge}**")

    st.subheader("Why these (in normal English)")
    for i, p in enumerate(picks, 1):
        reasons = _human_reasons(p)
        st.markdown(f"**Pick {i}:**")
        for r in reasons:
            st.write("• " + r)

def _human_reasons(p: Dict[str,Any]) -> List[str]:
    notes = p.get("notes","")
    reasons = []
    for a,b in re.findall(r"meta swapped (\d+)→(\d+)", notes):
        reasons.append(f"Swapped {a} for {b} because {b} looked better given the probabilities.")
    pulls = re.findall(r"shortlist pull (\d+)→(\d+)", notes)
    if pulls:
        reasons.append(f"Nudged {len(pulls)} number(s) toward the top-ranked shortlist.")
    m = re.search(r"EV swap lowered risk ([0-9.]+)→([0-9.]+)", notes)
    if m:
        x, y = m.groups()
        reasons.append(f"Reduced 'popular combo' risk from {float(x):.2f} to {float(y):.2f} to avoid splitting a jackpot.")
    m2 = re.search(r"conf[≈~=]?([0-9.]+)", notes)
    if m2:
        c = float(m2.group(1))
        reasons.append(f"Overall confidence for this set is about {int(c*100)}%.")
    # Badges
    if "diversity" in notes.lower():
        reasons.append("Diversity badge: this set was lightly mutated to increase difference from the others.")
    # Oracle
    if opt_oracle:
        parts = oracle_mods.get("parts", {})
        moon = parts.get("moon",0.0); mk = parts.get("markets",0.0)
        spc = parts.get("space",0.0); wierd = parts.get("weird",0.0)
        total = moon+mk+spc+wierd
        if total>0:
            reasons.append(f"Oracle signal applied (×{oracle_gain:.1f}): moon {moon*100:.0f}%, markets {mk*100:.0f}%, space {spc*100:.0f}%, alignments {wierd*100:.0f}%.")
    if opt_quantum:
        reasons.append(f"Blended probabilities across {quantum_universes} simulated universes; 'decoherence' {decoherence:.2f} softens extremes.")
    if opt_per_ball_ml:
        reasons.append("Per-ball ML looked at individual ball positions and nudged weights accordingly.")
    if opt_ev_mode and game != "pick3":
        reasons.append("We avoid common patterns (birthdays, sequences) when it doesn't hurt probability.")
    if diversity_min > 0 and game != "pick3":
        reasons.append(f"Diversity enforced: each set differs by at least {diversity_min} white number(s).")
    if special_max and min_unique_sp > 0 and game != "pick3":
        reasons.append(f"Special diversity: at least {min_unique_sp} unique special(s) across sets.")
    if hc_alpha > 0 and game != "pick3":
        reasons.append(f"Hot/Cold learning blended at {int(hc_alpha*100)}% with sharpness {hc_sharp:.1f}.")
    if opt_mc and mc_trials > 0 and game != "pick3":
        reasons.append(f"Monte Carlo synthesis ran {mc_trials} extra trials to surface stable combos.")
    return reasons or ["Standard frequency-based pick with small safety tweaks."]

c1, c2 = st.columns(2)
with c1:
    if st.button("Predict x1"):
        picks, W, Sp, _ = _predict(1)
        st.success("Generated 1 set.")
        _render_results(picks, W, Sp)
        if opt_viz:
            fig = render_white_surface(W, title="Probability Surface (white)")
            st.pyplot(fig)
with c2:
    if st.button("Predict x3"):
        picks, W, Sp, _ = _predict(3)
        st.success(f"Generated {len(picks)} sets.")
        _render_results(picks, W, Sp)
        if opt_viz:
            fig = render_white_surface(W, title="Probability Surface (white)")
            st.pyplot(fig)

# Info panels
def _hot_cold_panel():
    if df.empty:
        st.info("No history found for this game yet.")
        return

    counts = np.zeros(white_max+1, dtype=int)
    found_any = False
    for i in range(1, white_count+1):
        col = _find_col(df, ALT_WHITE(i))
        if col and (col in df.columns):
            found_any = True
            vals = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
            vals = vals[(vals>=white_min) & (vals<=white_max)].values
            for v in vals:
                counts[int(v)] += 1

    if not found_any or counts.sum() == 0:
        st.info("No frequency data available yet for hot/cold.")
        return

    order_hot = np.argsort(counts)[::-1]
    order_cold = np.argsort(counts)

    hot_list = []
    for idx in order_hot:
        if idx < white_min or idx > white_max:
            continue
        c = int(counts[idx])
        if c <= 0:
            break
        hot_list.append((int(idx), c))
        if len(hot_list) >= min(10, white_max):
            break

    cold_list = []
    nonzero = [i for i in range(white_min, white_max+1) if counts[i] > 0]
    if nonzero:
        for idx in order_cold:
            if idx < white_min or idx > white_max:
                continue
            c = int(counts[idx])
            if c <= 0:
                continue
            cold_list.append((int(idx), c))
            if len(cold_list) >= min(10, white_max):
                break
    else:
        cold_list = [(i, 0) for i in range(white_min, min(white_min+10, white_max+1))]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 Hot (most frequent)")
        st.write(", ".join([f"{n} ({c})" for n,c in hot_list]))
    with c2:
        st.subheader("🧊 Cold (least frequent)")
        st.write(", ".join([f"{n} ({c})" for n,c in cold_list]))

_hot_cold_panel()

def _next_draw_info():
    st.subheader("📅 Next draw & jackpot")
    schedules = {
        "powerball": dict(days=[0,2,5], hour=20, minute=59),
        "megamillions": dict(days=[1,4], hour=21, minute=0),
        "cash5": dict(days=list(range(7)), hour=19, minute=35),
        "pick3": dict(days=list(range(7)), hour=19, minute=35),
        "luckyforlife": dict(days=list(range(7)), hour=20, minute=38),
        "colorado_lottery": dict(days=list(range(7)), hour=19, minute=35),
    }
    now = dt.datetime.now()
    s = schedules.get(game, dict(days=list(range(7)), hour=20, minute=0))
    for i in range(8):
        cand = now + dt.timedelta(days=i)
        if cand.weekday() in s["days"]:
            draw_dt = cand.replace(hour=s["hour"], minute=s["minute"], second=0, microsecond=0)
            if draw_dt > now or i>0:
                break
    else:
        draw_dt = now

    def _norm(s): return s.strip().lower().replace(" ","").replace("_","").replace("-","")
    gk = _norm(game)
    jackpot_val = None
    if gk == _norm("powerball"):
        jackpot_val = jp.get_jackpot("powerball")
    elif gk == _norm("megamillions"):
        jackpot_val = jp.get_jackpot("megamillions")
    elif gk in (_norm("colorado_lottery"), _norm("colorado")):
        jackpot_val = jp.get_jackpot("colorado")
    jack_str = f"${jackpot_val:,}" if isinstance(jackpot_val, int) and jackpot_val>0 else "n/a"

    cols = st.columns(2)
    with cols[0]:
        st.metric("Next draw (est.)", draw_dt.strftime("%a %b %d, %I:%M %p"))
    with cols[1]:
        st.metric("Jackpot", jack_str)

_next_draw_info()

# Oracle panel (visual)
if opt_oracle:
    with st.expander("🔮 Oracle Influence Today"):
        parts = oracle_mods.get("parts", {})
        cols = st.columns(5)
        with cols[0]: st.metric("Moon", f"{parts.get('moon',0.0)*100:.1f}%")
        with cols[1]: st.metric("Markets", f"{parts.get('markets',0.0)*100:.1f}%")
        with cols[2]: st.metric("Space", f"{parts.get('space',0.0)*100:.1f}%")
        with cols[3]: st.metric("Alignments", f"{parts.get('weird',0.0)*100:.1f}%")
        with cols[4]: st.metric("Chaos add", f"{(oracle_chaos)*100:.1f}%")
        # Live context
        today = dt.date.today()
        st.caption(f"Moon: {moon_phase_bucket(today)} ({moon_phase_fraction(today)*100:.0f}% illuminated)")
        try:
            kp = kp_index_recent()
        except Exception:
            kp = None
        try:
            fl = solar_flare_activity()
        except Exception:
            fl = {"M": 0, "X": 0}
        try:
            v = market_volatility_proxy()
        except Exception:
            v = None
        st.caption(f"Kp: {kp if kp is not None else 'n/a'}; Flares 72h: M={fl.get('M',0)} X={fl.get('X',0)}")
        st.caption(f"VIX proxy: {v if v is not None else 'n/a'}")


# ---------------- Sidebar actions ----------------
def _train_all_games():
    status = []
    for g, fname in cache_map.items():
        path = DATA / fname
        if not path.exists():
            status.append(f"{g}: no data")
            continue
        try:
            dfg = pd.read_csv(path)
            _ = train_per_ball_ml(g, dfg, neg_per_pos=4)
            status.append(f"{g}: trained")
        except Exception as e:
            status.append(f"{g}: failed ({e})")
    return status

if do_train_all:
    st.sidebar.write("Training...")
    out = _train_all_games()
    st.sidebar.success("Done.")
    for line in out:
        st.sidebar.write(line)

# ---------------- Admin page router (via query param) ----------------
try:
    view = st.query_params.get("view", "")
    if isinstance(view, list):
        view = view[0] if view else ""
    if view == "admin":
        st.info("Open the Admin page from the left navigation (About → Admin).")
        st.stop()
except Exception:
    pass

# ---- Agents Section (no tabs detected) ----
import streamlit as st
with st.expander("AI Agents", expanded=False):
    _agent_mod = _import_first([
        "programs.pages.agent",
        "programs.agent",
        "agent",
    ])
    if not _call_first(_agent_mod):
        st.info("Agents page not found. Expected programs/pages/agent.py with render()/main().")