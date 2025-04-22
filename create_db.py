# create_db.py
"""
This script reads 'data/expenses.csv', reconstructs missing 'date' entries using 'year', 'month', and 'day_of_week',
adds UUIDs, and saves the result into 'data/expenses.db'.
"""

import sqlite3
import pandas as pd
import uuid
from pathlib import Path
import calendar
from datetime import datetime

# Define paths
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
CSV_PATH = DATA_DIR / "expenses.csv"
DB_PATH = DATA_DIR / "expenses.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
    year = int(row['year'])
    month = int(row['month'].split('-')[1]) if isinstance(row['month'], str) and '-' in row['month'] else int(row['month'])
    day_name = row['day_of_week']
    # Get all days in the month
    month_calendar = calendar.monthcalendar(year, month)
    # Find the first occurrence of the specified day_of_week
    for week in month_calendar:
        for i, day in enumerate(week):
            if day != 0 and calendar.day_name[i] == day_name:
                return datetime(year, month, day)
    return pd.NaT

# Apply reconstruction to missing dates
df.loc[missing_date_mask, 'date'] = df[missing_date_mask].apply(reconstruct_date, axis=1)

# Check if any 'date' entries are still missing
still_missing = df['date'].isnull().sum()
if still_missing > 0:
    print(f"⚠️ Warning: {still_missing} 'date' entries could not be reconstructed and will be dropped.")
    df = df.dropna(subset=['date'])

# Generate derived date columns
df['month'] = df['date'].dt.to_period('M').astype(str)
df['week'] = df['date'].dt.strftime('%G-W%V')  # ISO week format
df['day_of_week'] = df['date'].dt.day_name()

# Format 'date' as string
df['date'] = df['date'].dt.strftime('%Y-%m-%d')

# Add UUID as primary key
df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]

# Final schema validation
required_columns = {
    'date', 'account', 'category', 'sub_category', 'type',
    'user', 'amount', 'month', 'week', 'day_of_week'
}
missing_cols = required_columns - set(df.columns)
if missing_cols:
    raise ValueError(f"❌ Missing required column(s) after processing: {missing_cols}")

# Write to SQLite database
with sqlite3.connect(DB_PATH) as conn:
    df.to_sql("expenses", conn, if_exists="replace", index=False)

print(f"\n✅ Database successfully created at: {DB_PATH.resolve()}")
print(f"📊 Total records written: {len(df)}")
