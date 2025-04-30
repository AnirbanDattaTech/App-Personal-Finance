# streamlit/main.py
"""
Main Streamlit application file for the Personal Expense Tracker.
Handles page navigation and calls rendering functions for each tab.
ADDED 'budget' tab import and rendering logic.
"""
import streamlit as st
import pandas as pd
import logging
from pathlib import Path # Good practice for path handling

# --- ✅ Relative Imports for modules within the 'streamlit' package ---
# Assumes main.py is in the 'streamlit' directory
# and the tabs are in a subdirectory 'tabs'
# and utils are directly in 'streamlit'
try:
    # --- ADD 'budget' TO THE IMPORTS ---
    from tabs import add_expense, reports, visuals, assistant, budget # Added budget
    from style_utils import load_css
    from db_utils import fetch_all_expenses  # For CSV download
    st.session_state['imports_successful'] = True
    logging.info("Successfully imported UI tabs and utils.")
except ImportError as e:
    # This error handling is crucial for debugging if imports fail
    st.error(f"Failed to import necessary application components: {e}. "
             f"Please check the file structure and ensure main.py is run from the correct directory "
             f"or that the 'streamlit' package is correctly installed/recognized.")
    logging.exception("ImportError during initial module loading.")
    st.session_state['imports_successful'] = False
    st.stop() # Stop execution if core modules fail

# --- Configure basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Personal Expense Tracker",
    page_icon="💰"
)

# --- Load CSS ---
if st.session_state.get('imports_successful', False):
    load_css()
else:
    st.warning("Could not load CSS due to import errors.")

# --- Optional: Banner ---
# Consider adding specific styling in styles.css if uncommented
# st.markdown(
#     '<div class="app-banner">My Personal Finance App</div>',
#     unsafe_allow_html=True
# )

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    # --- ADD 'Budget' TO THE LIST OF OPTIONS ---
    ["Add Expenses", "Reports", "Visualizations", "Assistant", "Budget"], # Added Budget
    label_visibility="collapsed",
    key="main_nav"
)

st.sidebar.markdown("---")

# --- Sidebar Data Management ---
st.sidebar.header("Data Management")
if st.session_state.get('imports_successful', False): # Check if db_utils import worked
    try:
        # Fetch data using the imported function
        df_all = fetch_all_expenses()
        if not df_all.empty:
            # Optional: drop UUID if not needed for export
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
else:
    st.sidebar.warning("Data management unavailable due to import errors.")


# --- Page Rendering ---
# Only attempt to render if imports were successful
if st.session_state.get('imports_successful', False):
    if page == "Add Expenses":
        # Call the imported module's render function
        add_expense.render()
    elif page == "Reports":
        # Call the imported module's render function
        reports.render()
    elif page == "Visualizations":
        # Call the imported module's render function
        visuals.render()
    elif page == "Assistant":
         # --- ✅ Call the renamed Assistant tab's render function ---
         assistant.render() # **** CALL THE RENAMED MODULE'S FUNCTION ****
    # --- ADD RENDERING LOGIC FOR THE 'Budget' PAGE ---
    elif page == "Budget":
         budget.render() # Call the new budget tab's render function
    else:
        st.error("Invalid page selected.")
else:
    # Error message already displayed during import failure
    pass

# Optional: Add a footer or other common elements here if needed
# st.markdown("---")
# st.caption("App v1.1")