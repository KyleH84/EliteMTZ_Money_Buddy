
# === ADDED: robust render alias for app_main import ===
def render(*args, **kwargs):
    df = kwargs.get('df', None)
    symbols = kwargs.get('symbols', None)
    try:
        return render_watchlist(df=df, symbols=symbols)
    except Exception:
        try:
            return render_watchlist(df)
        except Exception:
            try:
                return render_watchlist_tab(df)
            except Exception:
                return None
