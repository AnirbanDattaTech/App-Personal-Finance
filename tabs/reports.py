# tabs/reports.py
import streamlit as st
import pandas as pd
from db_utils import fetch_all_expenses, fetch_expense_by_id, update_expense, delete_expense
import json
import datetime
from typing import Dict, Any, Optional, List
import logging # <<<--- ADD THIS IMPORT

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the expense_metadata.json file."""
    try:
        with open("expense_metadata.json", "r") as f:
            metadata = json.load(f)
            logging.debug("Metadata loaded successfully for Reports.")
            return metadata
    except FileNotFoundError:
        st.error("Error: expense_metadata.json not found.")
        logging.error("expense_metadata.json not found.")
        return None
    except json.JSONDecodeError:
        st.error("Error: Could not decode expense_metadata.json.")
        logging.error("Could not decode expense_metadata.json.")
        return None

@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """Converts a DataFrame to CSV bytes."""
    try:
        return df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        logging.error(f"Error converting DataFrame to CSV: {e}")
        return b""

# --- Function to display the Edit Form ---
def display_edit_form(expense_data: Dict[str, Any], metadata: Dict[str, Any]):
    """Displays the form for editing an existing expense."""
    # ... (Code inside this function is mostly okay, relies on db_utils logging) ...
    st.subheader(f"Edit Expense (ID: {expense_data.get('id', 'N/A')[:8]}...)")
    try: default_date = datetime.datetime.strptime(str(expense_data.get('date','')), '%Y-%m-%d').date()
    except: default_date = datetime.date.today()
    all_categories = sorted(list(metadata.get("categories", {}).keys()))
    all_accounts = metadata.get("Account", [])
    user_map = metadata.get("User", {})
    category_map = metadata.get("categories", {})
    default_category_index = 0
    if expense_data.get('category') in all_categories: default_category_index = all_categories.index(expense_data['category'])
    if 'edit_form_category' not in st.session_state: st.session_state.edit_form_category = all_categories[default_category_index] if all_categories else None
    def update_edit_category_state(): st.session_state.edit_form_category = st.session_state.edit_cat_widget
    selected_category = st.selectbox("Category", all_categories, index=default_category_index, key='edit_cat_widget', on_change=update_edit_category_state)
    current_category_in_state = st.session_state.edit_form_category
    available_subcategories = sorted(category_map.get(current_category_in_state, []))
    default_sub_cat_index = 0
    if expense_data.get('sub_category') in available_subcategories: default_sub_cat_index = available_subcategories.index(expense_data['sub_category'])
    default_account_index = 0
    if expense_data.get('account') in all_accounts: default_account_index = all_accounts.index(expense_data['account'])

    with st.form("edit_expense_form"):
        col1, col2 = st.columns(2)
        with col1:
            date_val = st.date_input("Date", value=default_date)
            account_val = st.selectbox("Account", all_accounts, index=default_account_index)
            sub_category_val = st.selectbox("Sub-category", available_subcategories, index=default_sub_cat_index, disabled=not available_subcategories)
        with col2:
            type_val = st.text_input("Type (Description)", value=expense_data.get('type',''), max_chars=60)
            user_val = user_map.get(account_val, "Unknown")
            st.text(f"User: {user_val}")
            amount_val = st.number_input("Amount (INR)", min_value=0.01, value=float(expense_data.get('amount', 0.01)), format="%.2f", step=10.0)
        submitted = st.form_submit_button("Save Changes")
        cancelled = st.form_submit_button("Cancel")
        if submitted:
            is_valid = True
            if not type_val: st.toast("⚠️ Type required.", icon="⚠️"); is_valid = False
            if amount_val <= 0.0: st.toast("⚠️ Amount must be positive.", icon="⚠️"); is_valid = False
            if available_subcategories and not sub_category_val: st.toast(f"⚠️ Sub-category required for {current_category_in_state}.", icon="⚠️"); is_valid = False
            elif sub_category_val and sub_category_val not in available_subcategories: st.toast(f"❌ Invalid sub-category '{sub_category_val}'.", icon="❌"); is_valid = False
            elif not available_subcategories and sub_category_val: st.toast(f"❌ No sub-categories exist for {current_category_in_state}.", icon="❌"); is_valid = False
            if is_valid:
                final_sub_category = sub_category_val if available_subcategories else ""
                updated_data = {"date": date_val.strftime("%Y-%m-%d"), "account": account_val, "category": current_category_in_state, "sub_category": final_sub_category, "type": type_val, "user": user_val, "amount": amount_val}
                try:
                    success = update_expense(st.session_state.selected_expense_id, updated_data)
                    if success:
                        st.toast("✅ Expense updated!", icon="✅")
                        st.session_state.edit_mode = False; st.session_state.pop('selected_expense_id', None); st.session_state.pop('edit_form_category', None); st.experimental_rerun()
                    else: st.toast("❌ Failed to update expense.", icon="❌") # db_utils logs specifics
                except Exception as e: st.toast(f"❌ Error: {e}", icon="❌"); logging.error(f"Update exception: {e}")
        if cancelled: st.session_state.edit_mode = False; st.session_state.pop('selected_expense_id', None); st.session_state.pop('edit_form_category', None); st.experimental_rerun()

# --- Function to display the Delete Confirmation ---
def display_delete_confirmation(expense_data: Dict[str, Any]):
    """Displays the confirmation dialog for deleting an expense."""
    # ... (Code inside this function is mostly okay, relies on db_utils logging) ...
    st.subheader("Confirm Deletion")
    st.warning(f"Permanently delete this expense?", icon="⚠️")
    col_details1, col_details2 = st.columns(2)
    with col_details1: st.markdown(f"**ID:** `{expense_data.get('id', 'N/A')[:8]}...`"); st.markdown(f"**Date:** {expense_data.get('date', 'N/A')}"); st.markdown(f"**Account:** {expense_data.get('account', 'N/A')}"); st.markdown(f"**User:** {expense_data.get('user', 'N/A')}")
    with col_details2: st.markdown(f"**Category:** {expense_data.get('category', 'N/A')}"); st.markdown(f"**Sub-Category:** {expense_data.get('sub_category', 'N/A')}"); st.markdown(f"**Type:** {expense_data.get('type', 'N/A')}"); st.markdown(f"**Amount:** ₹{float(expense_data.get('amount', 0)):.2f}")
    st.markdown("---")
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("Yes, Delete", type="primary"):
            try:
                success = delete_expense(st.session_state.selected_expense_id)
                if success: st.toast("🗑️ Expense deleted!", icon="🗑️"); st.session_state.delete_confirm = False; st.session_state.pop('selected_expense_id', None); st.experimental_rerun()
                else: st.toast("❌ Failed to delete.", icon="❌") # db_utils logs specifics
            except Exception as e: st.toast(f"❌ Error: {e}", icon="❌"); logging.error(f"Delete exception: {e}")
    with col_btn2:
        if st.button("No, Cancel"): st.session_state.delete_confirm = False; st.session_state.pop('selected_expense_id', None); st.experimental_rerun()

# --- Main Render Function for Reports Tab ---
def render():
    """Renders the 'Reports' page, handling normal view, edit mode, and delete confirmation."""
    # ... (Initialize session state) ...
    st.session_state.setdefault('edit_mode', False)
    st.session_state.setdefault('delete_confirm', False)
    st.session_state.setdefault('selected_expense_id', None)

    metadata = load_metadata()
    if metadata is None:
        return # Error shown in load_metadata

    # --- Conditional Rendering ---
    if st.session_state.edit_mode:
        if st.session_state.selected_expense_id:
            expense_to_edit = fetch_expense_by_id(st.session_state.selected_expense_id) # db_utils logs error
            if expense_to_edit: display_edit_form(expense_to_edit, metadata)
            else: st.error("Failed to load expense for editing."); st.session_state.edit_mode = False; # Reset
        else: st.error("No expense selected for edit."); st.session_state.edit_mode = False; # Reset
        # Add Back button if needed
        if st.session_state.edit_mode and st.button("Back to Report View##Edit"):
             st.session_state.edit_mode = False; st.session_state.pop('selected_expense_id', None); st.session_state.pop('edit_form_category', None); st.experimental_rerun()

    elif st.session_state.delete_confirm:
        if st.session_state.selected_expense_id:
            expense_to_delete = fetch_expense_by_id(st.session_state.selected_expense_id) # db_utils logs error
            if expense_to_delete: display_delete_confirmation(expense_to_delete)
            else: st.error("Failed to load expense for deletion."); st.session_state.delete_confirm = False; # Reset
        else: st.error("No expense selected for deletion."); st.session_state.delete_confirm = False; # Reset
        # Add Back button if needed
        if st.session_state.delete_confirm and st.button("Back to Report View##Delete"):
             st.session_state.delete_confirm = False; st.session_state.pop('selected_expense_id', None); st.experimental_rerun()

    else:
        # Render the normal report view if not editing or deleting
        try:
            render_report_view(metadata)
        except Exception as e:
            st.error(f"An error occurred while rendering the report: {e}")
            logging.exception("Error rendering report view.") # Log full traceback


# --- Helper Function for Normal Report View ---
def render_report_view(metadata: Dict[str, Any]):
    """Renders the standard report view with filters, stats, table, and actions."""
    st.subheader("Expense Report")

    df_all = fetch_all_expenses()
    if df_all.empty:
        st.info("No expense data.")
        return

    df_all['month'] = df_all['date'].dt.strftime('%Y-%m')
    all_accounts = metadata.get("Account", [])
    all_categories_map = metadata.get("categories", {})
    all_categories_list = sorted(list(all_categories_map.keys()))
    all_users_list = sorted(list(set(metadata.get("User", {}).values())))

    # --- Filter Section ---
    with st.expander("Filter Options", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            months = st.multiselect("Month", ["All"] + sorted(df_all['month'].unique(), reverse=True), default=["All"], key="report_months")
            accounts = st.multiselect("Account", ["All"] + all_accounts, default=["All"], key="report_accounts")
        with col2:
            categories = st.multiselect("Category", ["All"] + all_categories_list, default=["All"], key="report_categories")
            users = st.multiselect("User", ["All"] + all_users_list, default=["All"], key="report_users")
        with col3:
            if "All" in categories:
                sub_cats_options = sorted(list(set(sub for subs in all_categories_map.values() for sub in subs)))
            else:
                sub_cats_options = sorted(list(set(sub for cat in categories for sub in all_categories_map.get(cat, []))))
            subcategories = st.selectbox("Sub-category", ["All"] + sub_cats_options, key="report_subcat_select")

    # --- Apply Filters ---
    df_filtered = df_all.copy()
    if "All" not in months:
        df_filtered = df_filtered[df_filtered['month'].isin(months)]
    if "All" not in accounts:
        df_filtered = df_filtered[df_filtered['account'].isin(accounts)]
    if "All" not in categories:
        df_filtered = df_filtered[df_filtered['category'].isin(categories)]
    if subcategories != "All":
        df_filtered = df_filtered[df_filtered['sub_category'] == subcategories]
    if "All" not in users:
        df_filtered = df_filtered[df_filtered['user'].isin(users)]

    # --- Summary Stats ---
    total = df_filtered['amount'].sum()
    st.markdown(f"### Total Expense (Filtered): ₹{total:,.2f}")
    if not df_filtered.empty:
        st.markdown("---")
        st.markdown("#### Summary Statistics (Filtered Data)")
        num_transactions = len(df_filtered)
        avg_transaction = df_filtered['amount'].mean()
        top_category_series = df_filtered.groupby('category')['amount'].sum().nlargest(1)
        top_category_display = "N/A"
        if not top_category_series.empty:
            top_category_name = top_category_series.index[0]
            top_category_amount = top_category_series.iloc[0]
            top_category_display = f"{top_category_name} (₹{top_category_amount:,.0f})"
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric(label="Transactions", value=f"{num_transactions:,}")
        with stat_col2:
            st.metric(label="Avg. Transaction", value=f"₹{avg_transaction:,.2f}")
        with stat_col3:
            st.metric(label="Top Category", value=top_category_display)

    st.markdown("---")

    # --- Section Title + Right-Aligned Refresh Button ---
    col_left, col_spacer, col_right = st.columns([5, 1, 1])
    with col_left:
        st.markdown("#### Detailed Transactions")
    with col_right:
        if st.button("🔄 Refresh Data", help="Click to reload data from database"):
            st.session_state["force_refresh"] = True

    # ✅ Trigger hard rerun if refresh clicked
    if st.session_state.get("force_refresh", False):
        st.session_state["force_refresh"] = False
        st.rerun()

    display_df = pd.DataFrame()
    if not df_filtered.empty:
        display_df = df_filtered.drop(columns=["id", "month"], errors='ignore').rename(columns={
            "date": "Date",
            "account": "Account",
            "category": "Category",
            "sub_category": "Sub Category",
            "type": "Type",
            "user": "User",
            "amount": "Amount"
        }).sort_values("Date", ascending=False)

        st.dataframe(
            display_df.style.format({'Date': '{:%Y-%m-%d}', 'Amount': '₹{:.2f}'}),
            use_container_width=True,
            height=400,
            hide_index=True
        )
    else:
        st.info("No transactions match the current filters.")

    # --- Edit/Delete Panel ---
    if not df_filtered.empty:
        st.markdown("---")
        st.markdown("#### Edit / Delete Expense")
        options_limit = 500
        df_display_options = df_filtered.sort_values('date', ascending=False).head(options_limit).copy()
        df_display_options['display_str'] = df_display_options.apply(
            lambda row: f"{row['date'].strftime('%Y-%m-%d')} {row['account']} {row['category']} {row['sub_category'][:20]}.. ₹{row['amount']:.0f}", axis=1
        )
        options_dict = pd.Series(df_display_options.id.values, index=df_display_options.display_str).to_dict()
        options_dict = {"-- Select expense --": None, **options_dict}
        selected_option = st.selectbox("Select Expense to Modify", options=list(options_dict.keys()), key="expense_action_select")
        selected_id = options_dict.get(selected_option)

        col_action1, col_action2, _ = st.columns([1, 1, 4])
        edit_disabled = selected_id is None
        delete_disabled = selected_id is None

        with col_action1:
            if st.button("Edit Selected", key="edit_btn", disabled=edit_disabled):
                st.session_state.selected_expense_id = selected_id
                st.session_state.edit_mode = True
                st.session_state.pop('edit_form_category', None)
                st.experimental_rerun()

        with col_action2:
            if st.button("Delete Selected", key="delete_btn", disabled=delete_disabled):
                st.session_state.selected_expense_id = selected_id
                st.session_state.delete_confirm = True
                st.experimental_rerun()

    if not display_df.empty:
        st.markdown("---")
        csv_data = convert_df_to_csv(display_df)
        st.download_button("Export Filtered Data to CSV", csv_data, 'filtered_expenses.csv', 'text/csv', help="Download the currently displayed report as CSV.")
