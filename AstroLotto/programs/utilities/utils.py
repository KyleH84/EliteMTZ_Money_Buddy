
import os

def clear_prediction_log(filename: str):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception:
        pass
