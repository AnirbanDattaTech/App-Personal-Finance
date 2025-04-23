# streamlit/tabs/reports.py
import streamlit as st
import pandas as pd
import datetime
import json
import logging
from typing import Dict, Any, Optional
# Assuming db_utils is importable from streamlit/
from db_utils import fetch_all_expenses, fetch_expense_by_id, update_expense, delete_expense
from pathlib import Path
import time # Keep for short sleep after successful edit/delete

# Define Metadata Path relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_FILE_PATH = PROJECT_ROOT / "metadata" / "expense_metadata.json"

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the project's metadata directory."""
    if not METADATA_FILE_PATH.is_file():
        logging.error(f"Metadata file not found at: {METADATA_FILE_PATH}")
        st.error(f"Critical application error: Metadata configuration file not found at {METADATA_FILE_PATH}. Please ensure it exists.")
        return None
    try:
        with open(METADATA_FILE_PATH, "r") as f:
            metadata = json.load(f)
            logging.info(f"Metadata loaded successfully from {METADATA_FILE_PATH}")
            return metadata
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {METADATA_FILE_PATH}: {e}", exc_info=True)
        st.error(f"Critical application error: Metadata file ({METADATA_FILE_PATH.name}) seems corrupted. Please check its format.")
        return None
    except Exception as e:
        logging.exception(f"Failed to load or parse metadata from {METADATA_FILE_PATH}: {e}")
        st.error("Critical application error: An unexpected error occurred while loading metadata.")
        return None

@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """Converts a DataFrame to CSV bytes."""
    try:
        if 'Date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Date']):
             df_copy = df.copy()
             df_copy['Date'] = df_copy['Date'].dt.strftime('%Y-%m-%d')
             return df_copy.to_csv(index=False).encode("utf-8")
        else:
             return df.to_csv(index=False).encode("utf-8")
    except Exception as e:
        logging.error(f"CSV conversion failed: {e}")
        st.error("Failed to generate CSV data.")
        return b""

# ==============================================================================
# Main Rendering Function
# ==============================================================================
def render():
    """Renders the Reports page, handling view, edit, and delete modes."""
    st.session_state.setdefault("edit_mode", False)
    st.session_state.setdefault("delete_confirm", False)
    st.session_state.setdefault("selected_expense_id", None)
    st.session_state.setdefault("force_refresh", False)

    metadata = load_metadata()
    if metadata is None:
        return

    # --- ✅ Handle Refresh Request at the Top ---
    # If flag is set from previous run (e.g., after edit/delete/button press)
    if st.session_state.get("force_refresh", False):
        st.session_state["force_refresh"] = False # Reset the flag immediately
        st.cache_data.clear() # Clear cache to ensure fresh data fetch
        # No explicit message needed, just let the page reload below
        # The rerun itself is triggered by button clicks or state changes that set the flag

    # --- Mode Handling ---
    if st.session_state.edit_mode:
        if st.session_state.selected_expense_id:
            expense = fetch_expense_by_id(st.session_state.selected_expense_id)
            if expense:
                display_edit_form(expense, metadata)
            else:
                st.error(f"Could not load expense with ID {st.session_state.selected_expense_id} to edit.")
                st.session_state.edit_mode = False
                st.session_state.selected_expense_id = None
                if st.button("Back to Report"): st.rerun()
            return

    elif st.session_state.delete_confirm:
        if st.session_state.selected_expense_id:
            expense = fetch_expense_by_id(st.session_state.selected_expense_id)
            if expense:
                display_delete_confirmation(expense)
            else:
                st.error(f"Could not load expense with ID {st.session_state.selected_expense_id} to delete.")
                st.session_state.delete_confirm = False
                st.session_state.selected_expense_id = None
                if st.button("Back to Report"): st.rerun()
            return

    # --- Default Mode: Render Report View ---
    render_report_view(metadata)

# ==============================================================================
# Report View Rendering Function
# ==============================================================================
def render_report_view(metadata: Dict[str, Any]):
    """Displays the main report view with filters and data table."""
    st.subheader("Expense Report")

    # --- Fetch Data ---
    # This fetch happens on initial load or after a rerun triggered by refresh/edit/delete
    df_all = fetch_all_expenses()

    if df_all.empty:
        st.info("No expense data available to display.")
        return

    # --- Prepare Data and Filter Options ---
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_all['date']):
             df_all['date'] = pd.to_datetime(df_all['date'], errors='coerce')
             df_all.dropna(subset=['date'], inplace=True)

        if 'month' not in df_all.columns and 'date' in df_all.columns:
             df_all['month'] = df_all['date'].dt.strftime('%Y-%m')

        required_cols = ['date', 'month', 'account', 'category', 'sub_category', 'user', 'amount', 'id', 'type']
        if not all(col in df_all.columns for col in required_cols):
             missing = [col for col in required_cols if col not in df_all.columns]
             st.error(f"Database is missing required columns: {', '.join(missing)}. Cannot generate report.")
             logging.error(f"Missing columns in fetched data: {missing}")
             return

        all_months = ["All"] + sorted(df_all['month'].unique(), reverse=True)
        all_accounts = ["All"] + sorted(metadata.get("Account", []))
        all_categories = ["All"] + sorted(list(metadata.get("categories", {}).keys()))
        all_users = ["All"] + sorted(list(set(metadata.get("User", {}).values())))
        category_map = metadata.get("categories", {})
    except Exception as e:
         st.error(f"Error preparing data or filter options: {e}")
         logging.exception("Error during data preparation in reports tab.")
         return


    # --- Filter UI ---
    st.markdown("#### Filter Options")
    month_selected = st.selectbox(
        "Filter by Month", options=all_months, index=0, key="report_month_filter"
    )

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        accounts_selected = st.multiselect("Filter by Account(s)", options=all_accounts, default=["All"], key="report_account_filter")
        users_selected = st.multiselect("Filter by User(s)", options=all_users, default=["All"], key="report_user_filter")
    with filter_col2:
        categories_selected = st.multiselect("Filter by Category(s)", options=all_categories, default=["All"], key="report_category_filter")
        subcats_available = set()
        if "All" in categories_selected:
            for sublist in category_map.values(): subcats_available.update(sublist)
        else:
            for cat in categories_selected: subcats_available.update(category_map.get(cat, []))
        all_subcategories_options = ["All"] + sorted(list(subcats_available))
        subcategory_selected = st.selectbox(
            "Filter by Sub-category", options=all_subcategories_options, index=0, key="report_subcategory_filter",
            help="Available sub-categories depend on selected Categories."
        )

    # --- Apply Filters ---
    try:
        df_filtered = df_all.copy()
        if month_selected != "All": df_filtered = df_filtered[df_filtered['month'] == month_selected]
        if "All" not in accounts_selected: df_filtered = df_filtered[df_filtered['account'].isin(accounts_selected)]
        if "All" not in categories_selected: df_filtered = df_filtered[df_filtered['category'].isin(categories_selected)]
        if subcategory_selected != "All": df_filtered = df_filtered[df_filtered['sub_category'] == subcategory_selected]
        if "All" not in users_selected: df_filtered = df_filtered[df_filtered['user'].isin(users_selected)]
    except Exception as e:
         st.error(f"Error applying filters: {e}")
         logging.exception("Error occurred while filtering DataFrame.")
         df_filtered = pd.DataFrame()


    # --- Display Summary ---
    st.markdown("---")
    total_filtered_expense = df_filtered['amount'].sum() if not df_filtered.empty else 0
    st.markdown(f"### Total Expense (Filtered): ₹{total_filtered_expense:,.2f}")

    if not df_filtered.empty:
        st.markdown("#### Summary Statistics (Filtered)")
        num_transactions = len(df_filtered)
        avg_transaction_amount = df_filtered['amount'].mean()
        top_category_series = df_filtered.groupby("category")["amount"].sum().nlargest(1)
        top_category_display = "N/A"
        if not top_category_series.empty:
             top_category_display = f"{top_category_series.index[0]} (₹{top_category_series.values[0]:,.0f})"
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Transactions", f"{num_transactions:,}")
        stat_col2.metric("Avg. Transaction", f"₹{avg_transaction_amount:,.2f}")
        stat_col3.metric("Top Category", top_category_display)
    elif not df_all.empty:
        st.info("No transactions match the current filter criteria.")


    # --- Detailed Transactions Table ---
    st.markdown("---")
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
         st.markdown("### Detailed Transactions (Filtered)")
    with col_refresh:
        # --- Refresh Button just sets the flag and triggers rerun ---
        if st.button("🔄 Refresh Data", key="report_refresh_btn", help="Click to reload data from database"):
            st.session_state["force_refresh"] = True
            st.rerun() # Trigger rerun, flag will be checked at the top

    if not df_filtered.empty:
        display_columns = ["date", "account", "category", "sub_category", "type", "user", "amount"]
        existing_display_cols = [col for col in display_columns if col in df_filtered.columns]
        display_df = df_filtered[existing_display_cols + ['id']].copy()
        display_df = display_df.rename(columns={
            "date": "Date", "account": "Account", "category": "Category",
            "sub_category": "Sub Category", "type": "Type", "user": "User", "amount": "Amount (INR)"
        }).sort_values("Date", ascending=False)

        st.dataframe(
            display_df.drop(columns=['id']),
            column_config={
                 "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                 "Amount (INR)": st.column_config.NumberColumn("Amount (INR)", format="₹%.2f")
            },
            use_container_width=True, height=400, hide_index=True
        )

        # --- Edit / Delete Controls ---
        st.markdown("---")
        st.markdown("#### Edit / Delete Expense")
        df_selectable = display_df.copy().head(500)

        def create_display_label(row):
             date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'
             amt_str = f"₹{row['Amount (INR)']:.0f}"
             return f"{date_str} | {row['Category']} | {row.get('Sub Category', '')[:15]} | {row.get('Type', '')[:20]} | {amt_str}"

        selector_map = {"-- Select expense to modify --": None}
        for idx, row in df_selectable.iterrows():
             label = create_display_label(row)
             unique_label = f"{label} (ID: ...{row['id'][-6:]})"
             selector_map[unique_label] = row['id']

        selected_label = st.selectbox("Select Expense", options=list(selector_map.keys()), key="report_select_expense")
        selected_id = selector_map.get(selected_label)

        edit_col, delete_col = st.columns([1, 1])
        edit_disabled = selected_id is None
        delete_disabled = selected_id is None
        with edit_col:
            if st.button("Edit Selected", key="report_edit_btn", disabled=edit_disabled):
                st.session_state.selected_expense_id = selected_id
                st.session_state.edit_mode = True
                st.rerun()
        with delete_col:
            if st.button("Delete Selected", key="report_delete_btn", disabled=delete_disabled):
                st.session_state.selected_expense_id = selected_id
                st.session_state.delete_confirm = True
                st.rerun()

        # --- CSV Download Button ---
        st.markdown("---")
        csv_export_df = display_df.drop(columns=['id'])
        csv_data = convert_df_to_csv(csv_export_df)
        if csv_data:
            st.download_button(
                label="📥 Download Filtered Data (.csv)", data=csv_data,
                file_name="filtered_expenses.csv", mime="text/csv", key="report_download_csv"
            )
    # No final else needed here

# ==============================================================================
# Edit Form Display Function
# ==============================================================================
def display_edit_form(expense_data: Dict[str, Any], metadata: Dict[str, Any]):
    """Displays the form for editing a selected expense with dynamic sub-categories and rearranged layout."""
    expense_id = expense_data.get("id", "UNKNOWN")
    expense_id_short = f"...{expense_id[-6:]}" if expense_id != "UNKNOWN" else "N/A"
    st.subheader(f"Edit Expense (ID: {expense_id_short})")

    all_categories = sorted(metadata.get("categories", {}).keys())
    all_accounts = metadata.get("Account", [])
    user_map = metadata.get("User", {})
    category_map = metadata.get("categories", {})

    # --- Session State Initialization (as before) ---
    session_key_category = f"edit_category_{expense_id}"
    session_key_subcat_options = f"edit_subcat_options_{expense_id}"
    session_key_subcat_index = f"edit_subcat_index_{expense_id}"
    if session_key_category not in st.session_state:
        st.session_state[session_key_category] = expense_data.get("category", all_categories[0] if all_categories else None)

    # --- Callback (as before) ---
    def category_change_callback():
        new_category = st.session_state[f"edit_category_widget_{expense_id}"]
        st.session_state[session_key_category] = new_category
        new_subcat_options = sorted(category_map.get(new_category, []))
        st.session_state[session_key_subcat_options] = new_subcat_options
        st.session_state[session_key_subcat_index] = 0 # Reset index on category change

    # --- Get current state (as before) ---
    current_edit_category = st.session_state[session_key_category]
    current_subcat_options = st.session_state.get(session_key_subcat_options, sorted(category_map.get(current_edit_category, [])))

    try:
        # --- Pre-populate initial values (as before) ---
        default_date = pd.to_datetime(expense_data["date"]).date()
        default_account_index = all_accounts.index(expense_data["account"]) if expense_data["account"] in all_accounts else 0
        initial_category_index = all_categories.index(current_edit_category) if current_edit_category in all_categories else 0
        initial_subcat = expense_data.get("sub_category", "")
        initial_subcat_index = 0
        if initial_subcat and initial_subcat in current_subcat_options:
             initial_subcat_index = current_subcat_options.index(initial_subcat)
        if session_key_subcat_index not in st.session_state:
             st.session_state[session_key_subcat_index] = initial_subcat_index
        default_type = expense_data.get("type", "")
        default_amount = float(expense_data.get("amount", 0.01))

        # --- Widgets ABOVE the Form ---
        st.markdown("---") # Separator
        # --- ✅ Date Moved Here ---
        new_date_input = st.date_input("Date", value=default_date, key="edit_date_outside")
        # --- Category (triggers callback, stays outside form) ---
        st.selectbox(
            "Category",
            options=all_categories,
            index=initial_category_index,
            key=f"edit_category_widget_{expense_id}",
            on_change=category_change_callback
        )
        st.markdown("---") # Separator

        # --- Main Edit Form ---
        with st.form("edit_expense_form"):
            st.markdown("#### Modify Remaining Details")

            # --- ✅ Row 1: Account & Type ---
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                new_account_input = st.selectbox( # Changed variable name
                    "Account",
                    options=all_accounts,
                    index=default_account_index,
                    key="edit_account"
                )
            with row1_col2:
                new_type_input = st.text_input( # Changed variable name
                    "Type",
                    value=default_type,
                    key="edit_type",
                    max_chars=60
                )

            # --- ✅ Row 2: Sub-category & Amount ---
            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                 subcat_disabled = not bool(current_subcat_options)
                 current_subcat_idx = st.session_state.get(session_key_subcat_index, 0)
                 if current_subcat_idx >= len(current_subcat_options): current_subcat_idx = 0
                 new_subcat_input = st.selectbox( # Changed variable name
                      "Sub-category",
                      options=current_subcat_options,
                      index=current_subcat_idx,
                      key="edit_subcat_widget",
                      disabled=subcat_disabled,
                      help="Options update based on Category selected above."
                 )
            with row2_col2:
                 new_amount_input = st.number_input( # Changed variable name
                     "Amount (INR)",
                     value=default_amount,
                     min_value=0.01,
                     format="%.2f",
                     key="edit_amount"
                 )

            # --- User Display (Optional, Placed After Grid) ---
            derived_user = user_map.get(new_account_input, "Unknown")
            st.text(f"User: {derived_user}") # Display derived user

            # --- Form Submission Buttons ---
            submit_col, cancel_col = st.columns([1, 1])
            with submit_col: save_changes = st.form_submit_button("Save Changes")
            with cancel_col: cancel_edit = st.form_submit_button("Cancel")

            # --- Submission Logic ---
            if save_changes:
                # --- Read final values from widgets/state ---
                final_category = st.session_state[session_key_category]
                final_subcat_options = sorted(category_map.get(final_category, []))
                final_subcat_selection = new_subcat_input # Read from widget
                final_date = new_date_input # Read from widget outside form
                final_account = new_account_input # Read from widget
                final_type = new_type_input # Read from widget
                final_amount = new_amount_input # Read from widget

                # Validation
                is_valid = True
                if not final_type.strip(): st.warning("Type cannot be empty."); is_valid = False
                if final_amount <= 0: st.warning("Amount must be positive."); is_valid = False
                if final_subcat_options and not final_subcat_selection:
                    st.warning(f"Sub-category required for '{final_category}'."); is_valid = False
                if final_subcat_selection and final_subcat_selection not in final_subcat_options:
                     st.warning(f"'{final_subcat_selection}' is not valid for '{final_category}'."); is_valid = False

                if is_valid:
                     final_dt = pd.to_datetime(final_date)
                     updated_data = {
                        "date": final_dt.strftime("%Y-%m-%d"), "year": final_dt.year,
                        "month": final_dt.strftime("%Y-%m"), "week": final_dt.strftime("%G-W%V"),
                        "day_of_week": final_dt.day_name(), "account": final_account,
                        "category": final_category,
                        "sub_category": final_subcat_selection if final_subcat_options else "",
                        "type": final_type.strip(), "user": derived_user, "amount": final_amount
                     }
                     success = update_expense(expense_data["id"], updated_data)
                     if success:
                        st.success("Expense updated successfully!")
                        # Clean up state
                        for key in [session_key_category, session_key_subcat_options, session_key_subcat_index, f"edit_category_widget_{expense_id}"]:
                            if key in st.session_state: del st.session_state[key]
                        st.session_state.edit_mode = False
                        st.session_state.selected_expense_id = None
                        st.session_state["force_refresh"] = True
                        time.sleep(0.5)
                        st.rerun()
                     else:
                         st.error("Failed to update expense in the database.")

            elif cancel_edit:
                 # Clean up state
                 for key in [session_key_category, session_key_subcat_options, session_key_subcat_index, f"edit_category_widget_{expense_id}"]:
                     if key in st.session_state: del st.session_state[key]
                 st.session_state.edit_mode = False
                 st.session_state.selected_expense_id = None
                 st.rerun()

    except (ValueError, IndexError, KeyError, TypeError) as e:
         st.error(f"Error preparing edit form: {e}. Data might be inconsistent or type mismatch.")
         logging.exception(f"Error preparing edit form for ID {expense_id}: {e}")
         if st.button("Back to Report"):
              st.session_state.edit_mode = False; st.session_state.selected_expense_id = None; st.rerun()

# ==============================================================================
# Delete Confirmation Display Function
# ==============================================================================
def display_delete_confirmation(expense_data: Dict[str, Any]):
    """Displays the confirmation dialog for deleting an expense."""
    st.subheader("Confirm Deletion")
    st.warning(f"⚠️ Are you sure you want to permanently delete this expense?")

    details = {
        "Date": expense_data.get('date'), "Category": expense_data.get('category'),
        "Sub Category": expense_data.get('sub_category'), "Type": expense_data.get('type'),
        "Amount": f"₹{expense_data.get('amount', 0):,.2f}", "User": expense_data.get('user'),
        "Account": expense_data.get('account'), "ID": f"...{expense_data.get('id', '')[-6:]}"
    }
    st.json(details, expanded=True)

    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Yes, Delete Permanently", key="confirm_delete", type="primary"):
            success = delete_expense(expense_data["id"])
            if success:
                st.success("Expense deleted successfully.")
                st.session_state.delete_confirm = False
                st.session_state.selected_expense_id = None
                st.session_state["force_refresh"] = True # Trigger refresh
                time.sleep(0.5) # Brief pause
                st.rerun() # Rerun to show updated report
            else:
                 st.error("Failed to delete expense from the database.")
    with cancel_col:
        if st.button("Cancel", key="cancel_delete"):
            st.session_state.delete_confirm = False
            st.session_state.selected_expense_id = None
            st.rerun() # Go back to the report view