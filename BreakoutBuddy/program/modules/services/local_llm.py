from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path
from typing import Optional
try:
    import json
except Exception:
    json = None
_gpt = None
_model_file: Optional[Path] = None
def _config_path() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data" / "llm_config.json"
        if cand.exists():
            return cand
        if up.name == "program":
            cand2 = up.parent / "Data" / "llm_config.json"
            if cand2.exists():
                return cand2
    return (here.parent / "Data" / "llm_config.json")
def _read_model_dir() -> Optional[Path]:
    try:
        cfg_p = _config_path()
        if cfg_p.exists() and json is not None:
            with open(cfg_p, "r", encoding="utf-8") as f:
                data = json.load(f)
            d = data.get("model_dir")
            if d:
                p = Path(d)
                if p.exists():
                    return p
    except Exception:
        pass
    import os
    d = os.environ.get("LOCAL_LLM_DIR")
    if d and Path(d).exists():
        return Path(d)
    return None
def _pick_model(dir_path: Path) -> Optional[Path]:
    ggufs = sorted(dir_path.glob("*.gguf"))
    if not ggufs:
        return None
    ggufs.sort(key=lambda p: (('q4' not in p.name.lower()), ('7b' not in p.name.lower() and '8b' not in p.name.lower()), p.stat().st_size))
    for cand in ggufs:
        if cand.stat().st_size <= 6500000000:
            return cand
    return ggufs[0]
def is_available() -> bool:
    try:
        from gpt4all import GPT4All  # noqa: F401
    except Exception:
        return False
    d = _read_model_dir()
    if not d:
        return False
    m = _pick_model(d)
    return bool(m)
def _ensure_model_loaded() -> Optional[object]:
    global _gpt, _model_file
    if _gpt is not None:
        return _gpt
    try:
        from gpt4all import GPT4All
    except Exception:
        return None
    d = _read_model_dir()
    if not d:
        return None
    mf = _pick_model(d)
    if not mf:
        return None
    try:
        _model_file = mf
        _gpt = GPT4All(model_name=mf.name, model_path=str(mf.parent), allow_download=False)
        return _gpt
    except Exception:
        _gpt = None
        return None

def _infer_via_simple_api(prompt: str, *, max_tokens: int = 160, temp: float = 0.2) -> Optional[str]:
    """Optional tiny HTTP fallback if LLMBRIDGE_URL is set.
    Expects a JSON API that accepts: {"prompt": ..., "max_tokens": ..., "temperature": ...}
    and returns: {"text": "..."}.
    This stays inert unless LLMBRIDGE_URL is configured.
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
                # if not JSON, return raw text
                if data:
                    return data.strip()
        return None
    except Exception:
        return None



def infer(prompt: str, *, max_tokens: int = 160, temp: float = 0.2) -> Optional[str]:
    mdl = _ensure_model_loaded()
    if mdl is not None:
        try:
            out = mdl.generate(prompt, max_tokens=max_tokens, temp=temp)
            if isinstance(out, str):
                return out.strip()
            return str(out).strip()
        except Exception:
            pass
    # Local not available or failed; attempt optional simple API
    api_text = _infer_via_simple_api(prompt, max_tokens=max_tokens, temp=temp)
    if api_text:
        return api_text
    return None


# --- lightweight config/state helpers expected by Admin tab ---
_cfg_cache = {"model_dir":"", "preferred":""}

def _cfg_file() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data" / "llm_config.json"
        if cand.exists() or up.name == "program":
            return cand
    return here.parent / "Data" / "llm_config.json"

def _load_cfg():
    global _cfg_cache
    try:
        p = _cfg_file()
        if p.exists():
            import json as _json
            _cfg_cache.update(_json.loads(p.read_text()))
    except Exception:
        pass
    return _cfg_cache

def _save_cfg():
    try:
        p = _cfg_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        p.write_text(_json.dumps(_cfg_cache, indent=2))
    except Exception:
        pass

def get_config() -> dict:
    return dict(_load_cfg())

def set_model_dir(path: str) -> None:
    _load_cfg()
    _cfg_cache["model_dir"] = str(path or "").strip()
    _save_cfg()

def set_preferred_model(name: str) -> None:
    _load_cfg()
    _cfg_cache["preferred"] = str(name or "").strip()
    _save_cfg()

def list_models(dir_path: str | Path | None = None):
    d = Path(dir_path or _read_model_dir() or ".")
    return sorted([p.name for p in d.glob("*.gguf")]) if d.exists() else []

def rank_models(models):
    # Shallow heuristic: prefer q4_ files and 7B/8B instruct
    scored = []
    for m in models:
        ml = m.lower()
        s = 0.0
        if "instruct" in ml: s += 2
        if "q4" in ml: s += 1.5
        if ("7b" in ml) or ("8b" in ml): s += 1.0
        scored.append((m, s))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored

def suggest_best_model(models):
    r = rank_models(models)
    return r[0][0] if r else ""

def status() -> dict:
    d = _read_model_dir()
    return {
        "available": bool(is_available() and d and _pick_model(d)),
        "model_dir": str(d) if d else "",
        "preferred": _load_cfg().get("preferred",""),
    }

def open_model():
    try:
        return _ensure_model_loaded()
    except Exception:
        return None
