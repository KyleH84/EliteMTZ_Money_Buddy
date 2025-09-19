from datetime import datetime

class OpsHealthAgent:
    def __init__(self, freshness_checkers):
        self.fresh = freshness_checkers

    def check(self):
        now = datetime.utcnow()
        issues = []
        for name, fn in self.fresh.items():
            try:
                ts = fn()
                if hasattr(ts, 'timestamp'):
                    age = (now - ts).total_seconds()
                else:
                    age = float(ts)
                if age > 24 * 3600:
                    issues.append(f"{name} stale ({int(age/3600)}h)")
            except Exception as e:
                issues.append(f"{name} check failed: {e!s}")

        status = "green" if not issues else ("yellow" if len(issues) <= 2 else "red")
        return {"status": status, "issues": issues}
