# --- Import Libraries ---
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# --- Configuration (Optional) ---
pio.templates.default = "plotly_white"

print("--- Generating Sample Data ---")
# --- Generate Sample Data ---
dates = pd.date_range(start='2023-01-01', end='2023-01-31', freq='D')
# Using a different seed just to show it works, can revert to 42
np.random.seed(101)
values = np.random.randint(50, 150, size=len(dates))
df = pd.DataFrame({'Date': dates, 'DailyValue': values})

print("--- Calculating Cumulative Values ---")
# --- Calculate Cumulative Values ---
df['CumulativeValue'] = df['DailyValue'].cumsum()

print("\nSample Data with Cumulative Values (First 5 Rows):")
print(df.head())
print("\n" + "="*40 + "\n")

# --- Create Figure with Secondary Y-axis ---
print("--- Creating Combined Chart with Dual Y-Axes ---")

# Initialize figure
fig = go.Figure()

# --- Add Trace 1: Daily Value (Primary Y-axis - Left) ---
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['DailyValue'],
    name='Daily Value',
    mode='lines+markers',
    marker=dict(size=5),
    line=dict(width=2),
    yaxis='y1' # Assign to primary y-axis
))

# --- Add Trace 2: Cumulative Value (Secondary Y-axis - Right) ---
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['CumulativeValue'],
    name='Cumulative Value',
    mode='lines+markers',
    marker=dict(size=5),
    line=dict(width=2, dash='dash'),
    yaxis='y2' # Assign to secondary y-axis
))

# --- Update Layout for Dual Axes ---
fig.update_layout(
    title_text="Daily and Cumulative Values Over Time",
    xaxis_title="Date",

    # Configure Primary Y-axis (Left)
    yaxis=dict(
        # CORRECTED: title is a dict, font settings go inside 'font' key
        title=dict(
            text="Daily Value",
            font=dict(color="#1f77b4") # Color applied to title font
        ),
        tickfont=dict(color="#1f77b4"), # Tick labels color
        side='left'
    ),

    # Configure Secondary Y-axis (Right)
    yaxis2=dict(
        # CORRECTED: title is a dict, font settings go inside 'font' key
        title=dict(
            text="Cumulative Value",
            font=dict(color="#ff7f0e") # Color applied to title font
        ),
        tickfont=dict(color="#ff7f0e"), # Tick labels color
        side='right',
        overlaying='y',
        showgrid=False,
    ),

    legend_title_text="Metric",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

print("Displaying Combined Chart... (Check your browser)")
fig.show() # Display interactively

# --- Saving Static Image using Kaleido ---
print("\n--- Attempting to save combined chart as static PNG (using Kaleido) ---")
try:
    combined_chart_filename = "combined_daily_cumulative_chart.png"
    fig.write_image(combined_chart_filename, width=1000, height=500)
    print(f"Successfully saved: {combined_chart_filename}")

except ValueError as e:
     print(f"\nERROR: Could not save PNG image.")
     print(f"Please ensure Kaleido is installed correctly: pip install -U kaleido")
     print(f"Error details: {e}")
except Exception as e:
    print(f"\nAn unexpected error occurred during image saving: {e}")

print("\n--- Script Finished ---")