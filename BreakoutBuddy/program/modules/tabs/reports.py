from __future__ import annotations
# program/modules/tabs/reports.py
from typing import Any

# Re-export both spellings so app_main can import either modules.tabs.report or modules.tabs.reports
from .report import render_report_tab as render_report_tab  # noqa: F401
import streamlit as st

def render_reports_tab(*, settings: Any = None) -> None:
    # Some app_mains may call render_reports_tab; delegate to render_report_tab
    from .report import render_report_tab
    render_report_tab(settings=settings)