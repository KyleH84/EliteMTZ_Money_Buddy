
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

_CFG_NAME = "llm_config.json"

def _find_data_dir() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
        if up.name == "programs":
            cand2 = up.parent / "Data"
            if cand2.is_dir():
                return cand2
    fb = here.parent / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

def _cfg_path() -> Path:
    return _find_data_dir() / _CFG_NAME

def _load_cfg() -> Dict:
    p = _cfg_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_cfg(d: Dict) -> None:
    p = _cfg_path()
    try:
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass

def get_config() -> Dict:
    c = _load_cfg()
    c.setdefault("model_dir", "")
    c.setdefault("preferred_model", "")
    return c

def set_model_dir(path_str: str) -> None:
    c = get_config()
    c["model_dir"] = path_str.strip()
    _save_cfg(c)

def set_preferred_model(name: str) -> None:
    c = get_config()
    c["preferred_model"] = name.strip()
    _save_cfg(c)

def list_models(path_str: str | None = None) -> List[str]:
    try:
        p = Path(path_str) if path_str else Path(get_config().get("model_dir",""))
        if not p or not p.exists() or not p.is_dir():
            return []
        out = sorted([f.name for f in p.glob("*.gguf") if f.is_file()])
        return out
    except Exception:
        return []

def _parse_meta(name: str) -> Dict[str, bool]:
    n = name.lower()
    return {
        "is_instruct": ("instruct" in n) or ("chat" in n),
        "llama31": "llama-3.1" in n or "llama3.1" in n,
        "llama3": ("llama-3" in n or "llama3" in n) and ("3.1" not in n),
        "mistral": "mistral" in n,
        "qwen25": "qwen2.5" in n,
        "qwen2": "qwen2" in n and "qwen2.5" not in n,
        "q6k": "q6_k_" in n,
        "q5k": "q5_k_" in n,
        "q4k": "q4_k_" in n,
        "b8": "8b" in n,
        "b7": "7b" in n,
        "b4": "4b" in n,
        "b3": "3b" in n,
    }

def _score(name: str) -> float:
    m = _parse_meta(name)
    s = 0.0
    if m["llama31"]: s += 80
    elif m["llama3"]: s += 70
    elif m["mistral"]: s += 65
    elif m["qwen25"]: s += 63
    elif m["qwen2"]: s += 61
    if m["is_instruct"]: s += 15
    if m["b8"]: s += 12
    elif m["b7"]: s += 10
    elif m["b4"]: s += 5
    elif m["b3"]: s += 3
    if m["q6k"]: s += 6
    if m["q5k"]: s += 5
    if m["q4k"]: s += 4
    s -= len(name) * 0.001
    return s

def rank_models(models: List[str]) -> List[tuple[str, float]]:
    scored = [(nm, _score(nm)) for nm in models]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

def suggest_best_model(models: List[str]) -> Optional[str]:
    if not models: return None
    return rank_models(models)[0][0]

def status() -> Dict:
    c = get_config()
    model_dir = c.get("model_dir","")
    models = list_models(model_dir) if model_dir else []
    try:
        import gpt4all  # noqa: F401
        have_gpt4all = True
    except Exception:
        have_gpt4all = False
    preferred = c.get("preferred_model","")
    if preferred not in models:
        preferred = ""
    suggestion = suggest_best_model(models) if models else None
    ranked = rank_models(models) if models else []
    return {
        "have_gpt4all": have_gpt4all,
        "model_dir": model_dir,
        "models": models,
        "preferred_model": preferred,
        "suggested_best": suggestion or "",
        "ranked": ranked,
        "config_path": str(_cfg_path()),
    }

def open_model():
    st = status()
    if not st["have_gpt4all"]:
        return None
    models = st["models"]
    if not models:
        return None
    name = st["preferred_model"] or st["suggested_best"] or models[0]
    try:
        from gpt4all import GPT4All  # type: ignore
        m = GPT4All(name, model_path=st["model_dir"], allow_download=False)
        return m
    except Exception:
        return None


# --- Added safe helpers for optional API fallback ---
def is_available() -> bool:
    """True if a local GPT4All model is loadable OR an API bridge URL is set."""
    try:
        st = status()
        if st.get("have_gpt4all") and st.get("models"):
            return True
    except Exception:
        pass
    try:
        import os
        if os.environ.get("LLMBRIDGE_URL"):
            return True
    except Exception:
        pass
    return False

def _infer_via_simple_api(prompt: str, *, max_tokens: int = 200, temp: float = 0.2) -> Optional[str]:
    """Optional tiny HTTP fallback if LLMBRIDGE_URL is set.
    Expects a JSON API: {"prompt": "...", "max_tokens": 200, "temperature": 0.2} -> {"text": "..."}
    """
    try:
        import os, json, urllib.request
        url = os.environ.get("LLMBRIDGE_URL") or ""
        if not url:
            return None
        payload = json.dumps({"prompt": prompt, "max_tokens": max_tokens, "temperature": temp}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
            try:
                obj = json.loads(data)
                text = obj.get("text") or obj.get("output") or obj.get("response")
                if isinstance(text, str):
                    return text.strip()
            except Exception:
                if data:
                    return data.strip()
        return None
    except Exception:
        return None

def infer(prompt: str, *, max_tokens: int = 200, temp: float = 0.2) -> Optional[str]:
    """Try local GPT4All first; if unavailable, try the optional API bridge; else None."""
    try:
        m = open_model()
        if m is not None:
            try:
                with m.chat_session():
                    out = m.generate(prompt, max_tokens=max_tokens, temp=temp)
                if isinstance(out, str):
                    return out.strip()
                return str(out).strip()
            except Exception:
                pass
    except Exception:
        pass
    # Fallback to simple API if configured
    return _infer_via_simple_api(prompt, max_tokens=max_tokens, temp=temp)

