#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'kserc_dss.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

# Check schema for each table
for table_name, in tables:
    print(f"\n=== Table: {table_name} ===")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")

conn.close()
