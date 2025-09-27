# utilities/caching.py
import functools
import streamlit as st

cache_data = functools.partial(st.cache_data, ttl=900, show_spinner=False)
cache_resource = functools.partial(st.cache_resource, show_spinner=False)