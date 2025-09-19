# Optional UI helpers: proxy to top-level agents.ui_bits if present.
try:
    from agents.ui_bits import confidence_meter  # type: ignore
except Exception:
    def confidence_meter(score: float, conf: float):
        pass
