# streamlit/tabs/budget.py
"""
Renders the static 'Budget' tab UI based on predefined mock data.
"""
import streamlit as st
import plotly.graph_objects as go
import datetime
import pandas as pd # Using pandas for easy bar chart data creation

def create_budget_bar_chart(budget: float, spend: float, title: str) -> go.Figure:
    """Creates a simple Plotly bar chart comparing budget vs spend."""
    df = pd.DataFrame({
        'Category': ['Budget', 'Current Spend'],
        'Amount': [budget, spend]
    })

    fig = go.Figure()

    # Budget Bar
    fig.add_trace(go.Bar(
        x=['Budget'],
        y=[budget],
        name='Budget',
        marker_color='lightblue',
        text=f"₹{budget:,.0f}",
        textposition='outside',
        hoverinfo='name+y' # Show Budget: Amount on hover
    ))

    # Spend Bar
    fig.add_trace(go.Bar(
        x=['Current Spend'],
        y=[spend],
        name='Current Spend',
        marker_color='salmon',
        text=f"₹{spend:,.0f}",
        textposition='outside',
        hoverinfo='name+y' # Show Current Spend: Amount on hover
    ))

    # Customize layout
    fig.update_layout(
        title=dict(text=title, x=0.5, font_size=16),
        yaxis_title="Amount (INR)",
        xaxis_title=None, # Hide x-axis title
        xaxis=dict(showticklabels=False), # Hide x-axis labels
        yaxis=dict(range=[0, budget * 1.2]), # Set y-axis range based on budget
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        bargap=0.4, # Gap between bars within a category (doesn't apply much here)
        # barmode='group', # Default is group, explicit for clarity
        margin=dict(l=40, r=20, t=50, b=70), # Adjust margins
        height=300 # Set a fixed height for consistency
    )
    # Prevent y-axis hover info
    fig.update_yaxes(hoverformat = ".2f")

    return fig

def render():
    """Renders the Budget page mock UI."""
    st.subheader("💰 Monthly Budget Overview")

    # --- Mock Data ---
    # Get current month dynamically for display purposes
    # Note: In a real app, budget/spend would be fetched based on this month
    current_date = datetime.date.today()
    current_month_str = current_date.strftime("%B %Y") # e.g., "May 2025"

    mock_data = {
        "Anirban-ICICI": {"budget": 50000.0, "spend": 30000.0},
        "Anirban-SBI": {"budget": 10000.0, "spend": 4000.0}
    }

    col1, col2 = st.columns(2)

    # --- Column 1: Anirban-ICICI ---
    with col1:
        account_icici = "Anirban-ICICI"
        budget_icici = mock_data[account_icici]["budget"]
        spend_icici = mock_data[account_icici]["spend"]
        remaining_icici = budget_icici - spend_icici
        percent_remaining_icici = (remaining_icici / budget_icici) * 100 if budget_icici > 0 else 0

        st.markdown(f"#### {account_icici}")
        st.markdown(f"**Month:** {current_month_str}") # Display current month

        # Row 1: Budget Details
        row1_subcol1, row1_subcol2 = st.columns([0.7, 0.3]) # Allocate space for button
        with row1_subcol1:
            st.metric(label="Budget", value=f"₹{budget_icici:,.2f}")
        with row1_subcol2:
            st.button("Set Budget", key="set_budget_icici", help="Feature coming soon!", disabled=True) # Mock button

        st.metric(label="Current Spend", value=f"₹{spend_icici:,.2f}")
        st.metric(label="Remaining", value=f"₹{remaining_icici:,.2f}", delta=f"{percent_remaining_icici:.1f}% of budget")
        st.progress(spend_icici / budget_icici if budget_icici > 0 else 0) # Simple progress bar


        # Row 2: Bar Chart
        st.markdown("---") # Separator
        chart_icici = create_budget_bar_chart(budget_icici, spend_icici, f"{account_icici} Budget vs Spend")
        st.plotly_chart(chart_icici, use_container_width=True)


    # --- Column 2: Anirban-SBI ---
    with col2:
        account_sbi = "Anirban-SBI"
        budget_sbi = mock_data[account_sbi]["budget"]
        spend_sbi = mock_data[account_sbi]["spend"]
        remaining_sbi = budget_sbi - spend_sbi
        percent_remaining_sbi = (remaining_sbi / budget_sbi) * 100 if budget_sbi > 0 else 0

        st.markdown(f"#### {account_sbi}")
        st.markdown(f"**Month:** {current_month_str}") # Display current month

        # Row 1: Budget Details
        row1_subcol1_sbi, row1_subcol2_sbi = st.columns([0.7, 0.3])
        with row1_subcol1_sbi:
            st.metric(label="Budget", value=f"₹{budget_sbi:,.2f}")
        with row1_subcol2_sbi:
            st.button("Set Budget", key="set_budget_sbi", help="Feature coming soon!", disabled=True) # Mock button

        st.metric(label="Current Spend", value=f"₹{spend_sbi:,.2f}")
        st.metric(label="Remaining", value=f"₹{remaining_sbi:,.2f}", delta=f"{percent_remaining_sbi:.1f}% of budget")
        st.progress(spend_sbi / budget_sbi if budget_sbi > 0 else 0) # Simple progress bar


        # Row 2: Bar Chart
        st.markdown("---") # Separator
        chart_sbi = create_budget_bar_chart(budget_sbi, spend_sbi, f"{account_sbi} Budget vs Spend")
        st.plotly_chart(chart_sbi, use_container_width=True)