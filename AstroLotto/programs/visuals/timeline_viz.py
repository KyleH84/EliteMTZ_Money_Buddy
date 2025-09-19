# visuals/timeline_viz.py
import matplotlib.pyplot as plt
import numpy as np
def render_white_surface(white_probs, title="Probability Surface"):
    fig, ax = plt.subplots(figsize=(8,3))
    x = np.arange(1, len(white_probs)+1)
    ax.bar(x, white_probs)
    ax.set_title(title); ax.set_xlabel("Number"); ax.set_ylabel("Weight")
    fig.tight_layout()
    return fig
