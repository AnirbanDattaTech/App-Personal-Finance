# main.py
"""
Main Streamlit application file for the Personal Expense Tracker.
Handles page navigation and calls rendering functions for each tab.
"""
import streamlit as st
from tabs import add_expense, reports, visuals
from style_utils import load_css
import os # Import os for file path checking

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Personal Expense Tracker",
    page_icon="💰"
)

# --- Load CSS ---
# Ensure styles.css exists or handle the error gracefully in load_css
load_css() # Assumes styles.css exists in the same directory

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Add Expenses", "Reports", "Visualizations"],
    label_visibility="collapsed", # Cleaner look without the label "Go to" repeating
    key="main_nav" # Added a key for robustness
)

st.sidebar.markdown("---") # Visual separator

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
                mime="application/octet-stream", # Standard mime type for binary files
                help="Download the entire SQLite database file."
            )
    except OSError as e:
        st.sidebar.error(f"Error reading database file: {e}")
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
    # Fallback or error for unexpected page value
    st.error("Invalid page selected.")