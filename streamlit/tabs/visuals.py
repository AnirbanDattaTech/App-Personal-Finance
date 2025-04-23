# streamlit/tabs/visuals.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
# Assuming db_utils is importable from streamlit/
from db_utils import fetch_all_expenses
from typing import Dict, Any, Optional
import logging
from pathlib import Path

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
        st.error(f"Critical application error: Metadata file ({METADATA_FILE_PATH.name}) seems corrupted.")
        return None
    except Exception as e:
        logging.exception(f"Failed to load or parse metadata from {METADATA_FILE_PATH}: {e}")
        st.error("Critical application error: An unexpected error occurred while loading metadata.")
        return None

def get_common_layout_args(chart_title: str, show_legend: bool = False) -> Dict[str, Any]:
    """Generates common layout arguments for Plotly charts."""
    return {
        "title_text": chart_title,
        "title_font_size": 16, "title_x": 0.5,
        "margin": dict(l=20, r=20, t=50, b=80 if show_legend else 40),
        "legend": dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        "hovermode": "closest",
        "showlegend": show_legend
    }

def render():
    """Renders the 'Visualizations' page with a 2x2 grid of charts."""
    st.subheader("Expense Visualizations")

    metadata = load_metadata()
    if metadata is None: return

    # --- Fetch Data ---
    df_all = fetch_all_expenses()
    if df_all.empty:
        st.info("No expense data available for visualization.")
        return

    # --- Prepare Data ---
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_all['date']):
             df_all['date'] = pd.to_datetime(df_all['date'], errors='coerce')
             df_all.dropna(subset=['date'], inplace=True)

        if 'month' not in df_all.columns and 'date' in df_all.columns:
             df_all['month'] = df_all['date'].dt.strftime('%Y-%m') # Use 'month' consistently

        # Rename 'month' to 'YearMonth' for clarity if preferred, or just use 'month'
        if 'month' in df_all.columns and 'YearMonth' not in df_all.columns:
             df_all['YearMonth'] = df_all['month']

        # Check for required columns
        required_cols = ['YearMonth', 'category', 'amount', 'date', 'account', 'user', 'type', 'sub_category']
        if not all(col in df_all.columns for col in ['YearMonth', 'category', 'amount', 'date', 'account', 'user', 'type']):
             missing = [col for col in required_cols if col not in df_all.columns]
             st.error(f"Required columns missing for visualizations: {missing}")
             return

        min_date = df_all['date'].min().date()
        max_date = df_all['date'].max().date()
        all_months = ["All"] + sorted(df_all['YearMonth'].unique(), reverse=True)
        all_categories = ["All"] + sorted(list(metadata.get("categories", {}).keys()))
        all_users = ["All"] + sorted(list(set(metadata.get("User", {}).values())))
        all_accounts = ["All"] + sorted(metadata.get("Account", []))
    except Exception as e:
        st.error(f"Error preparing data or filter options: {e}")
        logging.exception("Error during data preparation in visuals tab.")
        return

    # --- Initialize Session State for Legends ---
    if 'legends' not in st.session_state:
        st.session_state.legends = {'pie': False, 'bar': False, 'line': False, 'top': False}

    # --- Layout for Charts ---
    st.markdown("#### Overview Charts")
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)

    # --- Chart 1: Pie Chart ---
    with row1_col1:
        st.markdown("###### By Category (Proportion)")
        # --- ✅ Updated Expander Label ---
        with st.expander("Pie Chart Filters", expanded=False):
            pie_month = st.selectbox("Month", all_months, 0, key="pie_month_filter")
            pie_cats = st.multiselect("Category", all_categories, ["All"], key="pie_cat_filter")
            pie_accounts = st.multiselect("Account", all_accounts, ["All"], key="pie_account_filter")
            pie_users = st.multiselect("User", all_users, ["All"], key="pie_user_filter")

        if st.button("Toggle Legend - Pie", key="pie_legend_btn"):
            st.session_state.legends['pie'] = not st.session_state.legends['pie']

        # Filter Data
        pie_df = df_all.copy()
        if pie_month != "All": pie_df = pie_df[pie_df['YearMonth'] == pie_month]
        if "All" not in pie_cats: pie_df = pie_df[pie_df['category'].isin(pie_cats)]
        if "All" not in pie_accounts: pie_df = pie_df[pie_df['account'].isin(pie_accounts)]
        if "All" not in pie_users: pie_df = pie_df[pie_df['user'].isin(pie_users)]

        # Aggregate and Plot
        pie_data = pie_df.groupby('category')['amount'].sum().reset_index()
        if not pie_data.empty and pie_data['amount'].sum() > 0:
            fig_pie = px.pie(pie_data, values='amount', names='category', hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', hoverinfo='label+percent+value')
            fig_pie.update_layout(**get_common_layout_args("Spending by Category", st.session_state.legends['pie']))
            st.plotly_chart(fig_pie, use_container_width=True)
        elif not pie_df.empty:
             st.info("No spending in selected categories/filters for Pie Chart.")
        else:
             st.info("No data matches filters for Pie Chart.")

    # --- Chart 2: Bar Chart ---
    with row1_col2:
        st.markdown("###### By Category (Absolute)")
        with st.expander("Bar Chart Filters", expanded=False):
            # ... (Filter widgets remain the same) ...
            bar_start = st.date_input("Start Date", min_date, key="bar_start_filter")
            bar_end = st.date_input("End Date", max_date, key="bar_end_filter")
            bar_accounts = st.multiselect("Account", all_accounts, ["All"], key="bar_account_filter")
            bar_users = st.multiselect("User", all_users, ["All"], key="bar_user_filter")


        if st.button("Toggle Legend - Bar", key="bar_legend_btn"):
            st.session_state.legends['bar'] = not st.session_state.legends['bar']

        # Filter Data (Remains the same)
        if bar_start > bar_end:
            st.warning("Start date cannot be after end date for Bar Chart.")
            bar_df = pd.DataFrame()
        else:
             bar_df = df_all[(df_all['date'].dt.date >= bar_start) & (df_all['date'].dt.date <= bar_end)]
             if "All" not in bar_accounts: bar_df = bar_df[bar_df['account'].isin(bar_accounts)]
             if "All" not in bar_users: bar_df = bar_df[bar_df['user'].isin(bar_users)]

        # Aggregate and Plot
        bar_data = bar_df.groupby('category')['amount'].sum().reset_index()
        if not bar_data.empty and bar_data['amount'].sum() > 0:
            fig_bar = px.bar(bar_data, x='category', y='amount', color='category', text_auto='.2s')

            # --- ✅ Modify Layout Update ---
            layout_bar = get_common_layout_args("Total Spending by Category", st.session_state.legends['bar'])
            layout_bar["yaxis_title"] = "Amount (INR)"
            layout_bar["xaxis_title"] = "Category"
            layout_bar["xaxis"] = dict(
                categoryorder='total descending',
                tickangle=-90  # Force vertical labels
            )
            fig_bar.update_layout(**layout_bar)
            # --- End of Modification ---

            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
        elif not bar_df.empty:
             st.info("No spending in selected categories/filters for Bar Chart.")
        else:
             st.info("No data matches filters for Bar Chart (check dates?).")


    # --- Chart 3: Line Chart ---
    with row2_col1:
        st.markdown("###### Trend Over Time")
        # --- ✅ Updated Expander Label ---
        with st.expander("Line Chart Filters", expanded=False):
            line_start = st.date_input("Start Date", min_date, key="line_start_filter")
            line_end = st.date_input("End Date", max_date, key="line_end_filter")
            line_cats = st.multiselect("Category", all_categories, ["All"], key="line_cat_filter")
            line_accounts = st.multiselect("Account", all_accounts, ["All"], key="line_account_filter")
            line_users = st.multiselect("User", all_users, ["All"], key="line_user_filter")
            line_mode = st.radio("View", ["Daily", "Cumulative"], 0, horizontal=True, key="line_mode_filter")

        if st.button("Toggle Legend - Line", key="line_legend_btn"):
            st.session_state.legends['line'] = not st.session_state.legends['line']

        # Filter Data
        if line_start > line_end:
             st.warning("Start date cannot be after end date for Line Chart.")
             line_df = pd.DataFrame()
        else:
            line_df = df_all[(df_all['date'].dt.date >= line_start) & (df_all['date'].dt.date <= line_end)]
            if "All" not in line_cats: line_df = line_df[line_df['category'].isin(line_cats)]
            if "All" not in line_accounts: line_df = line_df[line_df['account'].isin(line_accounts)]
            if "All" not in line_users: line_df = line_df[line_df['user'].isin(line_users)]

        # Aggregate and Plot
        trend_data = line_df.groupby('date')['amount'].sum().reset_index().sort_values('date')
        fig_line = go.Figure()
        trace_added = False
        if not trend_data.empty:
            if line_mode == "Daily":
                fig_line.add_trace(go.Scatter(x=trend_data['date'], y=trend_data['amount'], mode='lines+markers', name='Daily Spend'))
                trace_added = True
            elif line_mode == "Cumulative":
                trend_data['cumulative'] = trend_data['amount'].cumsum()
                fig_line.add_trace(go.Scatter(x=trend_data['date'], y=trend_data['cumulative'], mode='lines+markers', name='Cumulative Spend', line=dict(dash='dot')))
                trace_added = True

        if trace_added:
             layout_line = get_common_layout_args(f"{line_mode} Spending Trend", st.session_state.legends['line'])
             layout_line["yaxis_title"] = "Amount (INR)"
             layout_line["xaxis_title"] = "Date"
             layout_line["xaxis"] = dict(rangeslider=dict(visible=True), type="date")
             layout_line["hovermode"] = "x unified"
             fig_line.update_layout(**layout_line)
             st.plotly_chart(fig_line, use_container_width=True)
        elif not line_df.empty:
             st.info("No spending in selected categories/filters for Line Chart.")
        else:
             st.info("No data matches filters for Line Chart (check dates?).")

    # --- Chart 4: Top 10 Expense Types (Horizontal Bar) ---
    with row2_col2:
        st.markdown("###### Top 10 Expense Types")
        # --- ✅ Updated Expander Label ---
        with st.expander("Top Expenses Filters", expanded=False): # Renamed for clarity
            top_start = st.date_input("Start Date", min_date, key="top_start_filter")
            top_end = st.date_input("End Date", max_date, key="top_end_filter")
            top_cats = st.multiselect("Category", all_categories, ["All"], key="top_cat_filter")
            top_accounts = st.multiselect("Account", all_accounts, ["All"], key="top_account_filter")
            top_users = st.multiselect("User", all_users, ["All"], key="top_user_filter")

        # Toggle Button (Optional, maybe less useful here)
        # if st.button("Toggle Legend##Top", key="top_legend_btn"):
        #    st.session_state.legends['top'] = not st.session_state.legends['top']

        # Filter Data
        if top_start > top_end:
             st.warning("Start date cannot be after end date for Top Expenses.")
             top_df = pd.DataFrame()
        else:
            top_df = df_all[(df_all['date'].dt.date >= top_start) & (df_all['date'].dt.date <= top_end)]
            if "All" not in top_cats: top_df = top_df[top_df['category'].isin(top_cats)]
            if "All" not in top_accounts: top_df = top_df[top_df['account'].isin(top_accounts)]
            if "All" not in top_users: top_df = top_df[top_df['user'].isin(top_users)]

        # Aggregate by 'Type' and get top 10
        if not top_df.empty and 'type' in top_df.columns:
             # Handle potential NaN/empty types before grouping
            top_df_cleaned = top_df.dropna(subset=['type'])
            top_df_cleaned = top_df_cleaned[top_df_cleaned['type'].str.strip() != '']
            if not top_df_cleaned.empty:
                top_data = top_df_cleaned.groupby('type')['amount'].sum().reset_index().nlargest(10, 'amount').sort_values('amount', ascending=True)
                if not top_data.empty:
                    fig_top = px.bar(top_data, y='type', x='amount', orientation='h', text='amount', color='type', color_discrete_sequence=px.colors.qualitative.Pastel) # Example color sequence
                    layout_top = get_common_layout_args("Top 10 Expense Types by Amount", show_legend=False)
                    layout_top["xaxis_title"] = "Total Amount (INR)"
                    layout_top["yaxis_title"] = ""
                    layout_top["yaxis"] = {'categoryorder':'total ascending'}
                    fig_top.update_layout(**layout_top)
                    fig_top.update_traces(texttemplate="₹%{x:,.0f}", textposition="outside")
                    st.plotly_chart(fig_top, use_container_width=True)
                else:
                     st.info("No spending data found for 'Type' aggregation with current filters.")
            else:
                 st.info("No valid 'Type' entries found after cleaning filters.")
        elif not top_df.empty:
             st.info("No 'type' column found or no data after filtering for Top Expenses.")
        else:
             st.info("No data matches filters for Top Expenses (check dates?).")