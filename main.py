# main.py
"""
Main Streamlit application file for the Personal Expense Tracker.
Handles page navigation and calls rendering functions for each tab.
"""
import streamlit as st
from tabs import add_expense, reports, visuals
from style_utils import load_css
from db_utils import fetch_all_expenses  # ✅ To generate the CSV
import pandas as pd
import logging

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Personal Expense Tracker",
    page_icon="💰"
)

# --- Load CSS ---
load_css()

# --- Add Application Header Banner ---
st.title("My Personal Finance App")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Add Expenses", "Reports", "Visualizations"],
    label_visibility="collapsed",
    key="main_nav"
)

st.sidebar.markdown("---")

# --- Sidebar Data Management ---
st.sidebar.header("Data Management")
try:
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
    add_expense.render()
elif page == "Reports":
    reports.render()
elif page == "Visualizations":
    visuals.render()
else:
    st.error("Invalid page selected.")
