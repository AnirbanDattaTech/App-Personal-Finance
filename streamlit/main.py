# streamlit/main.py
"""
Main Streamlit application file for the Personal Expense Tracker.
Handles page navigation and calls rendering functions for each tab.
"""
import streamlit as st
# --- ✅ Relative Imports for modules within the 'streamlit' package ---
from tabs import add_expense, reports, visuals
from style_utils import load_css
from db_utils import fetch_all_expenses  # For CSV download
import pandas as pd
import logging
from pathlib import Path # Good practice for path handling

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Personal Expense Tracker",
    page_icon="💰"
)

# --- Load CSS ---
load_css()

# --- Optional: Banner ---
st.markdown(
    '<div class="app-banner">My Personal Finance App</div>',
    unsafe_allow_html=True
) # Consider adding specific styling in styles.css if uncommented

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    # --- ✅ Added 'Assistant' placeholder ---
    ["Add Expenses", "Reports", "Visualizations", "Assistant"],
    label_visibility="collapsed",
    key="main_nav"
)

st.sidebar.markdown("---")

# --- Sidebar Data Management ---
st.sidebar.header("Data Management")
try:
    # Fetch data using the relatively imported function
    df_all = fetch_all_expenses()
    if not df_all.empty:
        # Optional: drop UUID if not needed
        df_export = df_all.drop(columns=["id"], errors="ignore")
        csv_bytes = df_export.to_csv(index=False).encode("utf-8")

        st.sidebar.download_button(
            label="Download Data Backup (.csv)",
            data=csv_bytes,
            file_name="expenses_backup.csv",
            mime="text/csv",
            help="Download the full dataset as a CSV file"
        )
    else:
        st.sidebar.info("No expense data available to download.")
except Exception as e:
    st.sidebar.error("Error loading data for CSV backup.")
    logging.exception("Sidebar CSV export error: %s", e)

# --- Page Rendering ---
if page == "Add Expenses":
    # Call the relatively imported module's function
    add_expense.render()
elif page == "Reports":
    # Call the relatively imported module's function
    reports.render()
elif page == "Visualizations":
    # Call the relatively imported module's function
    visuals.render()
elif page == "Assistant":
     # --- ✅ Placeholder for the new Assistant tab UI ---
     st.subheader("Assistant")
     st.info("Chatbot interface coming soon!")
     # We will create and import streamlit.tabs.assistant_tab later
else:
    st.error("Invalid page selected.")