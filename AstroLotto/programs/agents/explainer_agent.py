from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from .state import RunState

def _try_local_llm_summary(state: RunState) -> str | None:
    try:
        from programs.services.local_llm import open_model  # type: ignore
        m = open_model()
        if m is None:
            return None
        s = state.artifacts
        o = s.oracle
        tele = s.telemetry or {}
        picks = s.picks or []
        top = picks[:3] if isinstance(picks, list) else []
        ctx = {
            "mode": getattr(state.inputs, "mode", ""),
            "diversity": float(tele.get("diversity_score", 0.0)),
            "ev": float(tele.get("ev_score", 0.0)),
            "oracle_gain": float(tele.get("oracle_gain", 1.0)),
            "kp": getattr(o, "kp_3h_max", 0.0) if o else 0.0,
            "vix": getattr(o, "vix_close", 0.0) if o else 0.0,
            "align": getattr(o, "alignment_index", 0.0) if o else 0.0,
            "retro": getattr(o, "mercury_retro", False) if o else False,
            "top_picks": top,
        }
        prompt = (
            "You are a lottery strategy assistant. Summarize the current run context and picks.\n"
            f"Context: {ctx}\n"
            "Write a one-line headline and 3-6 bullets: what to watch, risks, and caveats. "
            "Avoid hype and avoid probabilistic claims beyond the provided context."
        )
        with m.chat_session():
            out = m.generate(prompt, max_tokens=220, temp=0.2)
        return str(out).strip()
    except Exception:
        pass
    # Try optional API fallback if local model unavailable or failed
    try:
        from programs.services import local_llm as _llm
        txt = _llm.infer(prompt, max_tokens=220, temp=0.2)
        if txt:
            return txt
    except Exception:
        pass
    return None


def _fallback_narrative(state: RunState) -> str:
    try:
        s = state.artifacts
        o = s.oracle
        tele = s.telemetry or {}
        picks = s.picks or []
        top = picks[:3] if isinstance(picks, list) else []
        gain = float(tele.get("oracle_gain", 1.0))
        div  = float(tele.get("diversity_score", 0.0))
        ev   = float(tele.get("ev_score", 0.0))
        mode = getattr(state.inputs, "mode", "")

        pieces = []
        pieces.append(f"Mode {mode} with oracle gain {gain:.2f}. Diversity {div:.2f}, EV score {ev:.2f}.")
        if top:
            def _fmt_set(p):
                try:
                    w = p.get("white") or []
                    sp = p.get("special", None)
                    w_txt = ", ".join(str(int(x)) for x in w)
                    sp_txt = (f" +{int(sp)}" if sp not in (None, "",) else "")
                    return f"[{w_txt}]{sp_txt}"
                except Exception:
                    return "[...]"
            tops = ", ".join(_fmt_set(p) for p in top)
            pieces.append(f"Top candidates: {tops}.")
        if o:
            try:
                pieces.append(f"Context: VIX {getattr(o,'vix_close',0):.1f}, Kp {getattr(o,'kp_3h_max',0):.1f}, align {getattr(o,'alignment_index',0):.2f}, MercuryRetro {getattr(o,'mercury_retro', False)}.")
            except Exception:
                pass
        return " ".join(pieces).strip()
    except Exception:
        return "Standard conditions."

class ExplainerAgent:
    def summarize(self, state: RunState) -> str:
        s = state.artifacts
        o = s.oracle
        gain = float(s.telemetry.get("oracle_gain", 1.0))
        mode = state.inputs.mode
        div  = float(s.telemetry.get("diversity_score", 0.0))
        ev   = float(s.telemetry.get("ev_score", 0.0))

        header = (f"Top signals today — Oracle gain {gain:.2f}; "
                  f"Mode {mode}; Diversity {div:.2f}; EV {ev:.2f}")
        bullets = []

        if s.picks:
            try:
                pk = s.picks[0]
                if hasattr(pk, "why") and pk.why:
                    bullets.append(f"Best pick rationale: {pk.why}")
            except Exception:
                pass
            try:
                why = s.telemetry.get("why_hints", [])
                if why:
                    bullets.extend(why[:5])
            except Exception:
                pass

        flip = s.telemetry.get("flip_hint")
        if flip:
            bullets.append(f"If context calmed ({flip['condition']}), Ball {flip['ball']} would likely be {flip['to']}.")

        if o:
            bullets.append(f"Context: VIX {getattr(o,'vix_close',0):.1f}, "
                           f"Kp {getattr(o,'kp_3h_max',0):.1f}, "
                           f"Align {getattr(o,'alignment_index',0):.2f}, "
                           f"MercuryRetro {o.mercury_retro}")

        bullets = [f"• {b}" for b in bullets]
        text = header + ("\n" + "\n".join(bullets) if bullets else "")

        aug = _try_local_llm_summary(state)
        if aug:
            text += "\n\n" + "**Local model read**\n" + aug

        return text
