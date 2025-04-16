# main.py
"""
Main Streamlit application file for the Personal Expense Tracker.
Handles page navigation and calls rendering functions for each tab.
"""
import streamlit as st
from tabs import add_expense, reports, visuals
from style_utils import load_css
import os # Import os for file path checking
import logging # Ensure logging is imported if used within main

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Personal Expense Tracker",
    page_icon="💰"
)

# --- Load CSS ---
load_css() # Load custom styles first

# --- Add Application Header Banner ---
st.title("My Personal Finance App")
# --- End Application Header Banner ---

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
DB_FILE = "expenses.db"
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "rb") as fp:
            st.sidebar.download_button(
                label="Download Data Backup (.db)",
                data=fp,
                file_name="expenses_backup.db",
                mime="application/octet-stream",
                help="Download the entire SQLite database file."
            )
    except OSError as e:
        st.sidebar.error(f"Error reading database file: {e}")
        logging.error(f"Error reading DB for backup: {e}") # Log error
else:
    st.sidebar.warning("Database file not found for backup.")

# --- Page Rendering ---
if page == "Add Expenses":
    add_expense.render()
elif page == "Reports":
    reports.render()
elif page == "Visualizations":
    visuals.render()
else:
    st.error("Invalid page selected.")