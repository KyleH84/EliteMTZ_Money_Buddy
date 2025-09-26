from __future__ import annotations

from pathlib import Path
import os
import re
from collections import Counter
from typing import Optional

import streamlit as st

# page-local key namespace
_AGENT_KEY_PREFIX = "AL_AGENT_"
def _k(name: str) -> str:
    return f"{_AGENT_KEY_PREFIX}{name}"

# ------------------------------------------------------------
# Paths
# This file lives at AstroLotto/programs/pages/agent.py
# PROJECT_DIR -> .../AstroLotto/programs/pages
# APP_ROOT    -> .../AstroLotto
# DATA_DIR    -> .../AstroLotto/Data  (portable: always .\Data under app root)
# ------------------------------------------------------------
FILE_PATH = Path(__file__).resolve()
PROJECT_DIR = FILE_PATH.parent
APP_ROOT = FILE_PATH.parents[2]
DEFAULT_DATA_DIR = APP_ROOT / "Data"

def _effective_data_dir(ui_override: Optional[str]) -> Path:
    """
    Decide which Data folder to use.
    Priority:
      1) UI override (if provided and exists)
      2) Env var ASTROLOTTO_DATA_DIR (if set and exists)
      3) DEFAULT_DATA_DIR (.\Data under app root)
    """
    # 1) UI override
    if ui_override:
        cand = Path(ui_override)
        if cand.exists() and cand.is_dir():
            return cand

    # 2) Env var override
    env_path = os.environ.get("ASTROLOTTO_DATA_DIR")
    if env_path:
        cand = Path(env_path)
        if cand.exists() and cand.is_dir():
            return cand

    # 3) Default
    return DEFAULT_DATA_DIR

# ------------------------- Helpers -------------------------
def _infer_game_from_path(p: Optional[str]):
    p = (p or "").lower()
    if "powerball" in p:
        return "powerball", {"white_count":5, "white_min":1, "white_max":69, "special_min":1, "special_max":26, "has_special":True, "special_name":"PB"}
    if "mega" in p:
        return "megamillions", {"white_count":5, "white_min":1, "white_max":70, "special_min":1, "special_max":25, "has_special":True, "special_name":"MB"}
    if "cash5" in p or "cash 5" in p:
        return "cash5", {"white_count":5, "white_min":1, "white_max":32, "has_special":False}
    if "pick3" in p or "pick 3" in p:
        return "pick3", {"white_count":3, "white_min":0, "white_max":9, "has_special":False, "digits":True}
    if "lucky" in p:
        return "luckyforlife", {"white_count":5, "white_min":1, "white_max":48, "special_min":1, "special_max":18, "has_special":True, "special_name":"LB"}
    return "generic5p1", {"white_count":5, "white_min":1, "white_max":69, "special_min":1, "special_max":26, "has_special":True, "special_name":"S"}

def _parse_candidates_from_text(text: str, rules: dict):
    """Extract candidate tickets from free text. Returns list of dicts like:
       {"white":[...], "special": int|None}"""
    if not text:
        return []
    nums = [int(n) for n in re.findall(r"\b\d+\b", text)]
    out = []
    wcnt = rules.get("white_count",5)
    has_sp = rules.get("has_special", False)
    i = 0
    while i < len(nums):
        whites = nums[i:i+wcnt]
        i += wcnt
        special = None
        if has_sp and i < len(nums):
            special = nums[i]
            i += 1
        if len(whites) == wcnt:
            out.append({"white": whites, "special": special})
    return out

def _validate_and_clean(candidate: dict, rules: dict):
    """Return (ok, cleaned, reasons). Enforce ranges, sort whites, drop dups."""
    reasons = []
    whites = candidate.get("white", [])
    sp = candidate.get("special", None)
    wmin, wmax = rules.get("white_min",1), rules.get("white_max",69)
    wcnt = rules.get("white_count",5)
    has_sp = rules.get("has_special", False)
    smin, smax = rules.get("special_min",1), rules.get("special_max",26)

    w2 = []
    for x in whites:
        try:
            xi = int(x)
            if wmin <= xi <= wmax:
                w2.append(xi)
        except Exception:
            pass
    if len(w2) != len(whites):
        reasons.append("removed out-of-range whites")
    w2 = sorted(set(w2))[:wcnt]
    if len(w2) < wcnt:
        reasons.append(f"insufficient whites ({len(w2)}/{wcnt})")

    sp2 = None
    if has_sp:
        try:
            sp2 = int(sp) if sp is not None else None
        except Exception:
            sp2 = None
        if sp2 is not None and not (smin <= sp2 <= smax):
            reasons.append("special out of range")
            sp2 = None

    ok = (len(w2) == wcnt) and ((not has_sp) or (sp2 is not None))
    return ok, {"white": w2, "special": sp2}, reasons

def _hot_cold_from_csv(csv_path: str, rules: dict):
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return None, None
    cols = [c for c in df.columns if isinstance(c, str)]
    white_cols = [c for c in cols if re.search(r"(white|ball|w\d+)", c, re.I)]
    if not white_cols:
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        white_cols = numeric_cols[:rules.get("white_count",5)]
    sp_col = None
    if rules.get("has_special"):
        for c in cols:
            if re.search(r"(powerball|pb|mega|mb|special|star|lb)", c, re.I):
                sp_col = c
                break
    whites = []
    for c in white_cols:
        try:
            whites.extend([int(x) for x in df[c].dropna().tolist()])
        except Exception:
            pass
    specials = []
    if sp_col:
        try:
            specials = [int(x) for x in df[sp_col].dropna().tolist()]
        except Exception:
            specials = []
    wfreq = Counter([x for x in whites if rules["white_min"] <= x <= rules["white_max"]])
    sfreq = Counter([x for x in specials if rules.get("has_special") and rules["special_min"] <= x <= rules["special_max"]])
    return wfreq, sfreq

def _ev_penalties(whites: list[int], rules: dict):
    reasons = []
    penalty = 0.0
    low = sum(1 for x in whites if x <= 31)
    if low >= max(3, len(whites)-2):
        penalty += 0.6; reasons.append("many <=31 (birthday-heavy)")
    diffs = [whites[i+1]-whites[i] for i in range(len(whites)-1)]
    if len(diffs) and len(set(diffs)) == 1:
        penalty += 0.7; reasons.append("arithmetic sequence")
    if whites and all(x % 5 == 0 for x in whites):
        penalty += 0.5; reasons.append("all multiples of 5")
    if whites and (max(whites)-min(whites)) <= max(5, rules.get("white_max",69)//12):
        penalty += 0.4; reasons.append("very tight cluster")
    return penalty, reasons

def _score_candidate(c, wfreq, sfreq, rules):
    whites = sorted(c["white"])
    hot_score = sum(wfreq.get(x,0) for x in whites) if wfreq else 0
    sp_score = sfreq.get(c["special"], 0) if (sfreq and rules.get("has_special")) else 0
    base = hot_score + sp_score
    pen, pen_reasons = _ev_penalties(whites, rules)
    score = base - pen
    reasons = []
    if base>0: reasons.append(f"freq sum={base}")
    reasons += [f"-{r}" for r in pen_reasons] if pen_reasons else []
    return float(score), reasons

def _explain_candidate(c, wfreq, sfreq, rules):
    whites = sorted(c["white"])
    lines = [f"Whites: {whites}"]
    if rules.get("has_special"):
        lines.append(f"Special: {c['special']}")
    if wfreq:
        hottest = max(wfreq, key=wfreq.get)
        lines.append(f"Hottest white: {hottest} ({wfreq[hottest]} hits)")
    if sfreq and rules.get("has_special") and len(sfreq):
        hottsp = max(sfreq, key=sfreq.get)
        lines.append(f"Hottest special: {hottsp} ({sfreq[hottsp]} hits)")
    pen, pen_reasons = _ev_penalties(whites, rules)
    if pen_reasons:
        lines.append("EV cautions: " + ", ".join(pen_reasons))
    return "\\n".join(lines)

# ------------------------- Agent backend loader -------------------------
def _load_agent_response():
    """
    Returns (callable_or_None, last_error_tuple_or_None).
    Tries several modules for `agent_response(prompt, df_or_path=..., **kwargs)`.
    """
    import importlib
    candidates = [
        "programs.agent.langchain_lottery_agent",
        "programs.agent.main",
        "programs.agent.page",
        "agent",
    ]
    last_err = None
    for modname in candidates:
        try:
            mod = importlib.import_module(modname)
            fn = getattr(mod, "agent_response", None)
            if callable(fn):
                return fn, None
        except Exception as e:
            if last_err is None:
                last_err = (modname, e)
            continue
    return None, last_err

# ------------------------------- Page ----------------------------------
def render():
    st.title("AI Agent (Lottery Analysis)")
    st.caption("Ask about frequencies, patterns, or request plots.")

    # -------- Data source (.\\Data with override) --------
    st.write("### Data source")
    ui_override = st.text_input("Data folder (leave blank to use .\\Data)", str(DEFAULT_DATA_DIR), key=_k("agents_data_dir"))
    data_dir = _effective_data_dir(ui_override.strip() if ui_override else None)
    data_dir.mkdir(exist_ok=True, parents=True)

    csv_files = sorted({str(p.name) for p in data_dir.glob("*.csv")} | {str(p.name) for p in data_dir.glob("*.CSV")})
    if not csv_files:
        # Optional: shallow search inside subfolders of Data
        shallow = set()
        for sub in data_dir.iterdir():
            if sub.is_dir():
                shallow.update([str(p.name) for p in sub.glob("*.csv")])
                shallow.update([str(p.name) for p in sub.glob("*.CSV")])
        csv_files = sorted(shallow)

    default_name = "cached_powerball_data.csv"
    default_idx = csv_files.index(default_name) if default_name in csv_files else (0 if csv_files else -1)

    st.caption(f"Using Data folder: `{data_dir}` | found {len(csv_files)} CSV(s)  (env ASTROLOTTO_DATA_DIR also supported)")
    if csv_files:
        selected_csv = st.selectbox("CSV file", csv_files, index=max(default_idx, 0), key="agents_csv_select")
        csv_path = str(data_dir / selected_csv) if selected_csv else None
    else:
        st.warning("No CSVs found in the Data folder. Add files or set the override above.")
        csv_path = None

    # -------- Prompt + presets --------
    st.write("### Question")
    prompt = st.text_input("Your question", "What are the most frequent numbers?", key="agents_prompt")

    st.write("Agent presets")
    colp1, colp2, colp3, colp4 = st.columns(4)
    with colp1:
        if st.button("Top frequencies", key="agents_preset_freq"):
            prompt = "Compute and list the 15 most frequent white balls and specials by count."
    with colp2:
        if st.button("Hot vs Cold", key="agents_preset_hotcold"):
            prompt = "Summarize hot and cold numbers and explain any obvious patterns."
    with colp3:
        if st.button("Chart", key="agents_preset_chart"):
            prompt = "Create a bar chart of white-ball frequencies; return plotly figure."
    with colp4:
        if st.button("Pick suggestions", key="agents_preset_picks"):
            prompt = "Suggest 3 candidate ticket sets with diversity; explain why."

    # -------- Local models (optional) --------
    st.write("### Local models (optional)")
    gguf_dir = st.text_input("Folder with .gguf models", os.environ.get("GPT4ALL_MODELS_DIR", ""), key="agents_gguf_dir")
    auto_pick = None
    if gguf_dir and os.path.isdir(gguf_dir):
        try:
            candidates = [p for p in os.listdir(gguf_dir) if p.lower().endswith(".gguf")]
            if candidates:
                def _score(name: str):
                    name_l = name.lower()
                    base = 3 if "q5" in name_l else 2 if "q4" in name_l else 1 if ("q3" in name_l or "q2" in name_l) else 0
                    try:
                        size = os.path.getsize(os.path.join(gguf_dir, name))
                    except Exception:
                        size = 0
                    return (base, size)
                candidates.sort(key=_score, reverse=True)
                auto_pick = candidates[0]
                st.caption(f"Auto-picked model: `{auto_pick}`")
        except Exception as e:
            st.warning(f"Model scan error: {e}")
    if gguf_dir:
        os.environ["GPT4ALL_MODELS_DIR"] = gguf_dir

    run = st.button("Run", type="primary", key="agents_run")

    if run:
        agent_response, err = _load_agent_response()
        if agent_response is None:
            if err:
                modname, exc = err
                st.error(f"Failed to import `{modname}`: {exc}")
            else:
                st.error(
                    "Agents backend not found. Expected `agent_response` in one of: "
                    "`programs.agent.langchain_lottery_agent`, `programs.agent.main`, "
                    "`programs.agent.page`, or `agent`."
                )
            st.stop()

        try:
            df_or_path = csv_path
            # Try extended signature, fall back if not supported
            try:
                result = agent_response(prompt, df_or_path=df_or_path, gguf_dir=os.environ.get("GPT4ALL_MODELS_DIR"), auto_model=auto_pick)
            except TypeError:
                result = agent_response(prompt, df_or_path=df_or_path)

            rtype = (result or {}).get("type") if isinstance(result, dict) else None
            if rtype == "plotly" and isinstance(result.get("figure"), object):
                st.plotly_chart(result["figure"], use_container_width=True)
            elif rtype in ("matplotlib", "mpl") and result.get("figure") is not None:
                st.pyplot(result["figure"])
            elif rtype in ("dataframe", "table") and result.get("data") is not None:
                st.dataframe(result["data"])
            else:
                # Post-processing
                st.write("Post-processing")
                text_out = None
                if isinstance(result, str):
                    text_out = result
                elif isinstance(result, dict) and "text" in result:
                    text_out = str(result.get("text"))
                if text_out:
                    st.caption("Parsed candidates from agent text:")
                    game, rules = _infer_game_from_path(df_or_path)
                    raw_cands = _parse_candidates_from_text(text_out, rules)
                    valids = []
                    problems = []
                    for c in raw_cands:
                        ok, cleaned, why = _validate_and_clean(c, rules)
                        (valids if ok else problems).append((cleaned, why))
                    if not raw_cands:
                        st.write("(no numbers found)")
                    else:
                        for idx,(c,why) in enumerate(valids):
                            disp = f"{sorted(c['white'])}"
                            if rules.get('has_special'):
                                disp += f" + {rules.get('special_name','S')} {c['special']}"
                            st.write(f"✅ Candidate {idx+1}: {disp}")
                            if why: st.caption(", ".join(why))
                        for idx,(c,why) in enumerate(problems):
                            st.write(f"⚠️ Invalid set {idx+1}: {c}")
                            if why: st.caption(", ".join(why))

                    wfreq, sfreq = _hot_cold_from_csv(df_or_path, rules)
                    if wfreq is not None:
                        st.write("Hybrid scoring (hot/cold + EV cautions)")
                        scored = []
                        for c,_ in valids:
                            score, reasons = _score_candidate(c, wfreq, sfreq or Counter(), rules)
                            scored.append((score, c, reasons))
                        scored.sort(key=lambda x: x[0], reverse=True)
                        for rank,(score,c,reasons) in enumerate(scored, start=1):
                            disp = f"{sorted(c['white'])}"
                            if rules.get('has_special'):
                                disp += f" + {rules.get('special_name','S')} {c['special']}"
                            st.write(f"Rank {rank}: {disp}  (score {score:.2f})")
                            if reasons: st.caption("; ".join(reasons))

                        if scored:
                            opt_explain = st.selectbox("Explain which candidate?", list(range(1, len(scored)+1)), index=0, key="agents_explain_idx")
                            _, cand, _ = scored[opt_explain-1]
                            st.write("Explanation")
                            st.code(_explain_candidate(cand, wfreq, sfreq or Counter(), rules))

        except Exception as e:
            st.exception(e)


# Auto-render when executed by Streamlit as a page
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
    if get_script_run_ctx() is not None:
        render()
except Exception:
    render()