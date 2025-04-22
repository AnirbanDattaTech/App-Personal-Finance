# clean_expenses_csv.py
"""
This script reads 'data/expenses.csv', reconstructs missing 'date' entries using 'year', 'month', and 'day_of_week',
and writes the cleaned data back to 'data/expenses.csv'.
"""

import pandas as pd
import calendar
from datetime import datetime
from pathlib import Path

# Define paths
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
CSV_PATH = DATA_DIR / "expenses.csv"

# Load CSV
df = pd.read_csv(CSV_PATH)

# Normalize column names
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace("-", "_")
    .str.replace(" ", "_")
)

# Check if 'date' column exists; if not, create it
if 'date' not in df.columns:
    df['date'] = pd.NaT

# Convert 'date' column to datetime
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Identify rows with missing 'date' values
missing_date_mask = df['date'].isnull()

# Function to reconstruct date
def reconstruct_date(row):
    try:
        year = int(row['year'])
        month_str = str(row['month'])
        if '-' in month_str:
            month = int(month_str.split('-')[1])
        else:
            month = int(month_str)
        day_name = row['day_of_week']
        # Get all days in the month
        month_calendar = calendar.monthcalendar(year, month)
        # Find the first occurrence of the specified day_of_week
        for week in month_calendar:
            for i, day in enumerate(week):
                if day != 0 and calendar.day_name[i] == day_name:
                    return datetime(year, month, day)
    except Exception as e:
        pass
    return pd.NaT

# Apply reconstruction to missing dates
df.loc[missing_date_mask, 'date'] = df[missing_date_mask].apply(reconstruct_date, axis=1)

# Check if any 'date' entries are still missing
still_missing = df['date'].isnull().sum()
if still_missing > 0:
    print(f"⚠️ Warning: {still_missing} 'date' entries could not be reconstructed and will be dropped.")
    df = df.dropna(subset=['date'])

# Format 'date' as string
df['date'] = df['date'].dt.strftime('%Y-%m-%d')

# Write cleaned data back to CSV
df.to_csv(CSV_PATH, index=False)

print(f"\n✅ 'expenses.csv' has been cleaned and updated at: {CSV_PATH.resolve()}")
print(f"📊 Total records written: {len(df)}")
