"""
Agents package for BreakoutBuddy.
This file makes `modules.agents` a real Python package.

Re-exports:
    get_current_weights, run_agents_calibration
from .auto_tune (drop-in shipped earlier).
"""
from .auto_tune import get_current_weights, run_agents_calibration  # noqa: F401
import streamlit as st