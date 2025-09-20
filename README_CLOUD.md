# EliteMTZ Money Buddy — Cloud-Ready Build

This folder contains an auto-fixed version of your project intended to run cleanly on hosts like Streamlit Cloud, Codespaces, or any Linux container.

## How to run (Streamlit)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## How to run (plain Python)
If there's no Streamlit UI, run the entry module:
```bash
python EliteMTZ_Money_Buddy/home_main.py
```

## Notes
- All absolute file paths were redirected to project-local `data/` and `assets/` under `PROJECT_DIR`.
- Package imports were stabilized by adding `__init__.py` files.
- File writes create directories automatically.
- See `AUTO_AUDIT_REPORT.json` for a detailed summary of fixes.
