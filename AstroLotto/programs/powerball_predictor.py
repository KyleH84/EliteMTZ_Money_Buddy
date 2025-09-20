from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# -*- coding: utf-8 -*-

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import streamlit as st


# ---- Dynamic import helpers -------------------------------------------------
def _try_imports() -> Optional[Callable[..., Any]]:
    """Try to locate a backend function that returns Powerball predictions.

    We attempt several common module paths / function names used in prior versions.
    Returns a callable if found, else None.
    """
    import importlib

    candidates: List[Tuple[str, str]] = [
        ("utilities.prediction_core", "get_powerball_prediction"),
        ("models.powerball_model", "get_powerball_prediction"),
        ("models.powerball", "get_powerball_prediction"),
        ("models.powerball_model", "predict_powerball"),
        ("utilities.powerball_core", "get_powerball_prediction"),
        ("utilities.powerball_predictor_core", "get_powerball_prediction"),
        ("utilities.models.powerball_model", "get_powerball_prediction"),
        ("utilities.models.powerball", "get_powerball_prediction"),
        ("powerball_core", "get_powerball_prediction"),
        ("powerball_model", "get_powerball_prediction"),
        ("predictors.powerball", "get_powerball_prediction"),
        ("utilities.powerball_core", "predict_powerball"),
        ("utilities.powerball_predictor_core", "predict_powerball"),
    ]

    for mod, attr in candidates:
        try:
            m = importlib.import_module(mod)
            fn = getattr(m, attr, None)
            if callable(fn):
                return fn
        except Exception:
            # Swallow import errors and keep searching
            continue
    return None


# Cache the backend after first discovery
_PB_BACKEND: Optional[Callable[..., Any]] = None


def _load_backend() -> Optional[Callable[..., Any]]:
    global _PB_BACKEND
    if _PB_BACKEND is not None:
        return _PB_BACKEND
    _PB_BACKEND = _try_imports()
    return _PB_BACKEND


# ---- UI entry point ---------------------------------------------------------
def run_powerball_tab(*_: Any, **__: Any) -> None:
    st.header("Powerball")
    st.caption("Generate Powerball picks using your configured model and data.")

    # Basic controls
    colA, colB, colC = st.columns([1, 1, 1])
    with colA:
        n_picks = st.number_input(
            "How many picks?",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            help="Number of lines of numbers to return.",
        )
    with colB:
        use_hot_cold = st.toggle("Use Hot/Cold weighting", value=True)
    with colC:
        use_astro = st.toggle("Use Astro/Cosmic features (if available)", value=True)

    with st.expander("Advanced options", expanded=False):
        seed = st.number_input(
            "Random seed (optional)", min_value=0, max_value=10_000_000, value=0, step=1
        )
        allow_duplicates = st.toggle(
            "Allow duplicate white balls in a pick?", value=False
        )

    # Bundle args we pass through to the backend
    adv_kwargs: Dict[str, Any] = {
        "use_hot_cold": use_hot_cold,
        "use_astro": use_astro,
        "allow_duplicates": allow_duplicates,
    }
    if seed:
        adv_kwargs["seed"] = int(seed)

    backend = _load_backend()
    if backend is None:
        st.error(
            "Powerball backend function not found.\n\n"
            "Looking for a callable like `get_powerball_prediction` in one of:\n"
            "• utilities.powerball_core\n"
            "• utilities.powerball_predictor_core\n"
            "• models.powerball_model\n"
            "• powerball_model / predictors.powerball\n\n"
            "If your predictor lives elsewhere, either:\n"
            "1) Rename your function to `get_powerball_prediction` and place it in one of those modules, or\n"
            "2) Add a new (module, function) tuple to the `candidates` list in this file."
        )
        return

    if st.button("🎯 Generate Powerball Predictions", type="primary", width="stretch"):
        tried: List[str] = []
        result: Any = None

        # Try common calling conventions in a safe order
        for callstyle in ("n_picks_kwargs", "kwargs_only", "n_picks_only"):
            try:
                if callstyle == "n_picks_kwargs":
                    result = backend(int(n_picks), **adv_kwargs)  # type: ignore[misc]
                elif callstyle == "kwargs_only":
                    result = backend(**adv_kwargs)  # type: ignore[misc]
                else:
                    result = backend(int(n_picks))  # type: ignore[misc]
                if result is not None:
                    break
            except TypeError as te:
                tried.append(f"{backend.__name__}({callstyle}) -> {te}")
            except Exception as e:
                tried.append(f"{backend.__name__}({callstyle}) -> {type(e).__name__}: {e}")

        if result is None:
            st.error(
                "Could not call backend with any known signature:\n\n- "
                + "\n- ".join(tried)
            )
            return

        picks = _normalize_predictions(result, allow_duplicates=allow_duplicates)
        if not picks:
            st.warning("Backend returned no predictions.")
            return

        # Pretty print
        for i, p in enumerate(picks[: int(n_picks)], 1):
            white = ", ".join(f"{int(x):02d}" for x in p["white"])
            special = int(p["special"])
            st.write(f"**Pick {i}:** {white}  |  Powerball: **{special:02d}**")


# ---- Normalization ----------------------------------------------------------
def _normalize_predictions(
    result: Any, allow_duplicates: bool = False
) -> List[Dict[str, Any]]:
    """Normalize various backend return shapes to:
        List[{'white': List[int], 'special': int}]
    Accepts:
      • {'white': [...], 'special': n}
      • {'picks': [{'white': [...], 'special': n}, ...]}
      • [[white_list, special], ...] or [(white_list, special), ...]
      • pandas.DataFrame with columns like white1..white5, powerball|special
      • pandas.Series of that shape
      • numpy arrays of shape (k, >=2)
    """
    out: List[Dict[str, Any]] = []

    def _as_int_list(seq: Any) -> List[int]:
        try:
            # Handles lists/tuples/np arrays/Series
            return [int(v) for v in list(seq)]
        except Exception:
            return []

    # Pandas / NumPy friendly path
    try:
        import pandas as pd  # noqa: WPS433
        import numpy as np  # noqa: WPS433

        if isinstance(result, pd.DataFrame):
            cols = [c for c in result.columns]
            # Try common column patterns
            white_cols = [c for c in cols if str(c).lower().startswith("white")]
            if not white_cols:
                # Fallback guess: first 5 numeric columns as whites
                white_cols = [c for c in cols if pd.api.types.is_numeric_dtype(result[c])][:5]
            special_col = None
            for cand in ("powerball", "special", "pb", "red"):
                if cand in result.columns:
                    special_col = cand
                    break
            if special_col is None:
                # Try a numeric column after whites
                num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(result[c])]
                if len(num_cols) > len(white_cols):
                    special_col = num_cols[len(white_cols)]

            for _, row in result.iterrows():
                whites = _as_int_list([row[c] for c in white_cols])
                special = int(row.get(special_col, 0) or 0)
                whites, special = _clean_pb_numbers(whites, special, allow_duplicates)
                if whites and special:
                    out.append({"white": whites, "special": special})
            return out

        if isinstance(result, pd.Series):
            # Treat like a single-pick DataFrame row
            return _normalize_predictions(result.to_frame().T, allow_duplicates)

        if isinstance(result, np.ndarray):
            # Expect rows of [whites..., special]
            for row in result:
                whites = _as_int_list(row[:-1])
                special = int(row[-1])
                whites, special = _clean_pb_numbers(whites, special, allow_duplicates)
                if whites and special:
                    out.append({"white": whites, "special": special})
            return out
    except Exception:
        # Pandas/Numpy not available or something went sideways; continue below
        pass

    # Dict-like shapes
    if isinstance(result, dict):
        if "white" in result and "special" in result:
            whites = _as_int_list(result["white"])
            special = int(result["special"])
            whites, special = _clean_pb_numbers(whites, special, allow_duplicates)
            if whites and special:
                out.append({"white": whites, "special": special})
        elif "picks" in result and isinstance(result["picks"], list):
            for item in result["picks"]:
                if isinstance(item, dict) and "white" in item and "special" in item:
                    whites = _as_int_list(item["white"])
                    special = int(item["special"])
                    whites, special = _clean_pb_numbers(whites, special, allow_duplicates)
                    if whites and special:
                        out.append({"white": whites, "special": special})
        return out

    # Sequence of picks: list of dicts or (whites, special)
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, dict) and "white" in item and "special" in item:
                whites = _as_int_list(item["white"])
                special = int(item["special"])
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                whites = _as_int_list(item[0])
                special = int(item[1])
            else:
                continue
            whites, special = _clean_pb_numbers(whites, special, allow_duplicates)
            if whites and special:
                out.append({"white": whites, "special": special})

    return out


def _clean_pb_numbers(
    whites: Sequence[int], special: int, allow_duplicates: bool
) -> Tuple[List[int], int]:
    """Enforce Powerball ranges and duplicate policy.
    Whites: 1..69, Special: 1..26
    """
    # Coerce and clamp to valid ranges
    w = [min(69, max(1, int(x))) for x in whites]
    if not allow_duplicates:
        # Keep first occurrence order, drop duplicates
        seen = set()
        w = [x for x in w if not (x in seen or seen.add(x))]
    # Powerball special
    s = min(26, max(1, int(special)))
    # Typical pick shows 5 white balls; if fewer, we still return what we have
    return w[:5], s
