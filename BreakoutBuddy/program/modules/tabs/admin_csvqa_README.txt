
# Patch note: ensure your BreakoutBuddy/modules/tabs/admin.py calls `_section_csv_qa()`
# Example:
# def render_admin_tab(**kwargs):
#     st.header("Admin")
#     _section_llm()
#     _section_csv_qa()
