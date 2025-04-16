import sqlite3
import pandas as pd
import uuid

# Load CSV
df = pd.read_csv("dummy_expenses.csv")

# Normalize column names
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace("-", "_")
    .str.replace(" ", "_")
)

# Validate and format date
df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')

# Add UUID for each row
df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]

# Save to SQLite
conn = sqlite3.connect("expenses.db")
df.to_sql("expenses", conn, if_exists="replace", index=False)
conn.close()

print("✅ Database 'expenses.db' created from CSV!")
