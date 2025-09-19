"""Predictor engines for AstroLotto V14.

This package defines pluggable engines for generating lottery
predictions.  The main entry points are:

* :func:`ensemble.predict_sets` for the ensemble engine that blends
  long/short and gap/overdue signals.  It optionally includes
  pair synergy if requested.
* :func:`montecarlo.predict_sets` for the Monte Carlo engine built
  atop ``utilities.montecarlo_v2``.

These engines return lists of dictionaries with at least keys
``"white"`` and ``"special"`` matching the data format used by
``app_main.py``.

"""
__all__ = ["ensemble", "montecarlo"]