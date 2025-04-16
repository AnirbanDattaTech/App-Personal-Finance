# tabs/visuals.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
from db_utils import fetch_all_expenses
from typing import Dict, Any, Optional, List
import logging # <<<--- ADD THIS IMPORT

@st.cache_data
def load_metadata() -> Optional[Dict[str, Any]]:
    """Loads metadata from the expense_metadata.json file."""
    try:
        with open("expense_metadata.json", "r") as f:
            metadata = json.load(f)
            logging.debug("Metadata loaded successfully for Visuals.")
            return metadata
    except FileNotFoundError:
        st.error("Error: expense_metadata.json not found.")
        logging.error("expense_metadata.json not found.")
        return None
    except json.JSONDecodeError:
        st.error("Error: Could not decode expense_metadata.json.")
        logging.error("Could not decode expense_metadata.json.")
        return None

# --- Helper function for common Plotly layout args ---
def get_common_layout_args(chart_title: str) -> Dict[str, Any]:
    """Returns a dictionary of common Plotly layout arguments."""
    # ... (function remains the same) ...
    return {
        "title_text": chart_title, "title_font_size": 16, "title_x": 0.5,
        "margin": dict(l=10, r=10, t=40, b=20),
        "legend": dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        "hovermode": "closest",
    }


def render():
    """Renders the 'Visualizations' page with a 2x2 grid of charts."""
    st.subheader("Expense Visualizations")

    metadata = load_metadata()
    if metadata is None:
        return # Error already shown

    # Fetch all data (uncached)
    df_all = fetch_all_expenses() # This function now logs internally on error
    if df_all.empty:
        st.info("No expense data available for visualizations.")
        return

    # --- Data Preprocessing & Filter List Setup ---
    try:
        # Ensure date conversion doesn't fail silently
        df_all['date'] = pd.to_datetime(df_all['date'], errors='raise') # Raise error if conversion fails
        df_all['YearMonth'] = df_all['date'].dt.strftime('%Y-%m')
        min_date_overall = df_all['date'].min().date()
        max_date_overall = df_all['date'].max().date()
        all_months = ["All"] + sorted(df_all['YearMonth'].unique(), reverse=True)
        all_categories = ["All"] + sorted(list(metadata.get("categories", {}).keys()))
        all_users = ["All"] + sorted(list(set(metadata.get("User", {}).values())))
        all_accounts = ["All"] + metadata.get("Account", [])
        treemap_parent_categories = sorted(list(metadata.get("categories", {}).keys()))
    except Exception as e:
        st.error(f"Error processing initial data: {e}")
        logging.exception("Data preprocessing error in visuals.") # Log full traceback
        return

    # --- Create 2x2 Grid Layout ---
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # Wrap each chart rendering in a try-except block for robustness
    try:
        # --- Chart 1: Pie Chart (Top-Left) ---
        with col1:
            st.markdown("#### By Category (Proportion)")
            with st.expander("Filters", expanded=False):
                f_col1, f_col2 = st.columns(2)
                with f_col1: pie_month = st.selectbox("Month", all_months, 0, key="pie_month_select"); pie_categories = st.multiselect("Category", all_categories, ["All"], key="pie_category_select")
                with f_col2: pie_accounts = st.multiselect("Account", all_accounts, ["All"], key="pie_account_select"); pie_users = st.multiselect("User", all_users, ["All"], key="pie_user_select")
            # Filter logic...
            pie_df = df_all.copy();
            if pie_month != "All": pie_df = pie_df[pie_df['YearMonth'] == pie_month]
            if "All" not in pie_accounts: pie_df = pie_df[pie_df['account'].isin(pie_accounts)]
            if "All" not in pie_categories: pie_df = pie_df[pie_df['category'].isin(pie_categories)]
            if "All" not in pie_users: pie_df = pie_df[pie_df['user'].isin(pie_users)]
            if pie_df.empty: st.info("No data: Pie", icon="ℹ️")
            else:
                pie_data = pie_df.groupby('category')['amount'].sum().reset_index(); pie_data = pie_data[pie_data['amount'] > 0]
                if pie_data.empty: st.info("No positive data: Pie", icon="ℹ️")
                else:
                    chart_title = f"Category Spend ({pie_month})"; fig1 = px.pie(pie_data, values='amount', names='category', hole=0.4)
                    fig1.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>%{label}</b><br>Amt: ₹%{value:,.0f}<br>(%{percent})<extra></extra>", insidetextorientation='radial')
                    layout_args = get_common_layout_args(chart_title); layout_args["showlegend"] = False; fig1.update_layout(**layout_args)
                    st.plotly_chart(fig1, use_container_width=True)
    except Exception as e:
        logging.exception("Error rendering Pie Chart.")
        st.error("Error displaying Pie Chart.", icon="🔥")


    try:
        # --- Chart 2: Category Bar Chart (Top-Right) ---
        with col2:
            st.markdown("#### By Category (Absolute)")
            with st.expander("Filters", expanded=False):
                 f_col1, f_col2 = st.columns(2)
                 with f_col1: cat_bar_start_date = st.date_input("Start Date", min_date_overall, min_date_overall, max_date_overall, key="cat_bar_start_date"); cat_bar_accounts = st.multiselect("Account", all_accounts, ["All"], key="cat_bar_account_select")
                 with f_col2: cat_bar_end_date = st.date_input("End Date", max_date_overall, min_date_overall, max_date_overall, key="cat_bar_end_date"); cat_bar_users = st.multiselect("User", all_users, ["All"], key="cat_bar_user_select")
            # Filter logic...
            cat_bar_df = df_all.copy(); date_range_valid = cat_bar_start_date <= cat_bar_end_date
            if date_range_valid:
                cat_bar_df = cat_bar_df[(cat_bar_df['date'].dt.date >= cat_bar_start_date) & (cat_bar_df['date'].dt.date <= cat_bar_end_date)]
                if "All" not in cat_bar_accounts: cat_bar_df = cat_bar_df[cat_bar_df['account'].isin(cat_bar_accounts)]
                if "All" not in cat_bar_users: cat_bar_df = cat_bar_df[cat_bar_df['user'].isin(cat_bar_users)]
            else: st.warning("Invalid date: Cat Bar", icon="⚠️"); cat_bar_df = pd.DataFrame()
            if cat_bar_df.empty: st.info("No data: Cat Bar", icon="ℹ️")
            else:
                cat_bar_data = cat_bar_df.groupby('category')['amount'].sum().reset_index(); cat_bar_data = cat_bar_data[cat_bar_data['amount'] > 0].sort_values('amount', ascending=False)
                if cat_bar_data.empty: st.info("No positive data: Cat Bar", icon="ℹ️")
                else:
                    chart_title = f"Category Totals ({cat_bar_start_date.strftime('%d%b')}-{cat_bar_end_date.strftime('%d%b%y')})"; fig2 = px.bar(cat_bar_data, x='category', y='amount', color='category')
                    fig2.update_traces(hovertemplate="<b>%{x}</b><br>Total: ₹%{y:,.0f}<extra></extra>")
                    layout_args = get_common_layout_args(chart_title); layout_args["showlegend"] = False; layout_args["xaxis_title"] = None; layout_args["yaxis_title"] = "Total (INR)"; layout_args["xaxis"] = dict(categoryorder='total descending', tickangle=-90); layout_args["margin"]["b"] = 80
                    fig2.update_layout(**layout_args)
                    st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        logging.exception("Error rendering Category Bar Chart.")
        st.error("Error displaying Category Bar Chart.", icon="🔥")


    try:
        # --- Chart 3: Line Chart (Bottom-Left) ---
        with col3:
            st.markdown("#### Trend Over Time")
            with st.expander("Filters", expanded=False):
                f_col1, f_col2 = st.columns(2)
                with f_col1: line_start_date = st.date_input("Start Date", min_date_overall, min_date_overall, max_date_overall, key="line_start_date"); line_categories = st.multiselect("Category", all_categories, ["All"], key="line_category_select"); line_chart_mode = st.radio("View", ["Daily", "Cumulative"], 0, key="line_chart_mode_select", horizontal=True)
                with f_col2: line_end_date = st.date_input("End Date", max_date_overall, min_date_overall, max_date_overall, key="line_end_date"); line_accounts = st.multiselect("Account", all_accounts, ["All"], key="line_account_select"); line_users = st.multiselect("User", all_users, ["All"], key="line_user_select")
            # Filter logic...
            line_df_filtered = pd.DataFrame(); date_range_valid = line_start_date <= line_end_date
            if date_range_valid:
                line_df_filtered = df_all[(df_all['date'].dt.date >= line_start_date) & (df_all['date'].dt.date <= line_end_date)].copy()
                if "All" not in line_accounts: line_df_filtered = line_df_filtered[line_df_filtered['account'].isin(line_accounts)]
                if "All" not in line_categories: line_df_filtered = line_df_filtered[line_df_filtered['category'].isin(line_categories)]
                if "All" not in line_users: line_df_filtered = line_df_filtered[line_df_filtered['user'].isin(line_users)]
            else: st.error("Invalid date: Line Chart", icon="🚨");
            if line_df_filtered.empty:
                if date_range_valid: st.info("No data: Line Chart", icon="ℹ️")
            else:
                trend_data = line_df_filtered.groupby('date')['amount'].sum().reset_index().sort_values('date');
                if trend_data.empty: st.info("No spending: Line Chart", icon="ℹ️")
                else:
                    fig3 = go.Figure(); chart_title = f'{line_chart_mode} Trend ({line_start_date.strftime("%d%b")}-{line_end_date.strftime("%d%b%y")})'; yaxis_title = f'{line_chart_mode} Amount (INR)'
                    trace_args = {"x": trend_data['date'], "mode": 'lines+markers', "marker": dict(size=4)}
                    if line_chart_mode == "Daily": fig3.add_trace(go.Scatter(**trace_args, y=trend_data['amount'], name='Daily', line=dict(width=2), hovertemplate="<b>%{x|%d %b %Y}</b><br>Daily: ₹%{y:,.0f}<extra></extra>"))
                    elif line_chart_mode == "Cumulative": trend_data['cumulative_amount'] = trend_data['amount'].cumsum(); fig3.add_trace(go.Scatter(**trace_args, y=trend_data['cumulative_amount'], name='Cumulative', line=dict(width=2, dash='dot'), hovertemplate="<b>%{x|%d %b %Y}</b><br>Cumulative: ₹%{y:,.0f}<extra></extra>"))
                    layout_args = get_common_layout_args(chart_title); layout_args["yaxis_title"] = yaxis_title; layout_args["xaxis_title"] = None; layout_args["showlegend"] = False; layout_args["hovermode"] = "x unified"; layout_args["xaxis"] = dict(rangeslider=dict(visible=True), type="date")
                    fig3.update_layout(**layout_args)
                    st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        logging.exception("Error rendering Line Chart.")
        st.error("Error displaying Line Chart.", icon="🔥")


    try:
        # --- Chart 4: Sub-category Treemap (Bottom-Right) ---
        with col4:
            st.markdown("#### Sub-Category Breakdown")
            with st.expander("Filters", expanded=False):
                default_parent_index = treemap_parent_categories.index("Grocery") if "Grocery" in treemap_parent_categories else 0
                treemap_parent_category = st.selectbox("Category to Break Down", treemap_parent_categories, index=default_parent_index, key="treemap_parent_select")
                st.markdown("---")
                f_col1, f_col2 = st.columns(2)
                with f_col1: treemap_start_date = st.date_input("Start Date", min_date_overall, min_date_overall, max_date_overall, key="treemap_start_date"); treemap_accounts = st.multiselect("Account", all_accounts, ["All"], key="treemap_account_select")
                with f_col2: treemap_end_date = st.date_input("End Date", max_date_overall, min_date_overall, max_date_overall, key="treemap_end_date"); treemap_users = st.multiselect("User", all_users, ["All"], key="treemap_user_select")
            # Filter logic...
            treemap_df = df_all.copy(); treemap_df = treemap_df[treemap_df['category'] == treemap_parent_category]
            date_range_valid = treemap_start_date <= treemap_end_date
            if date_range_valid:
                treemap_df = treemap_df[(treemap_df['date'].dt.date >= treemap_start_date) & (treemap_df['date'].dt.date <= treemap_end_date)]
                if "All" not in treemap_accounts: treemap_df = treemap_df[treemap_df['account'].isin(treemap_accounts)]
                if "All" not in treemap_users: treemap_df = treemap_df[treemap_df['user'].isin(treemap_users)]
            else: st.warning("Invalid date: Treemap", icon="⚠️"); treemap_df = pd.DataFrame()
            if treemap_df.empty: st.info(f"No '{treemap_parent_category}' data: Treemap", icon="ℹ️")
            else:
                treemap_data = treemap_df.groupby('sub_category')['amount'].sum().reset_index(); treemap_data = treemap_data[treemap_data['amount'] > 0]
                if treemap_data.empty: st.info(f"No positive spending: '{treemap_parent_category}' sub-cats.", icon="ℹ️")
                else:
                    chart_title = f"'{treemap_parent_category}' Breakdown ({treemap_start_date.strftime('%d%b')}-{treemap_end_date.strftime('%d%b%y')})"; fig4 = px.treemap(treemap_data, path=[px.Constant(treemap_parent_category), 'sub_category'], values='amount', color='sub_category', custom_data=['amount'])
                    fig4.update_traces(hovertemplate='<b>%{label}</b><br>Amt: ₹%{customdata[0]:,.0f}<br>% of Parent: %{percentParent:.1%}<extra></extra>', textinfo='label+value', insidetextfont=dict(size=12))
                    layout_args = get_common_layout_args(chart_title); layout_args["showlegend"] = False; fig4.update_layout(**layout_args)
                    st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        logging.exception("Error rendering Treemap Chart.")
        st.error("Error displaying Treemap Chart.", icon="🔥")