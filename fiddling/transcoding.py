import sqlite3
import csv

db_path = "../data/data.db"
csv_path = "fund_code_export.csv"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('SELECT * FROM FUND_CODE')
rows = cur.fetchall()

# Get column names
col_names = [description[0] for description in cur.description]

with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(col_names)
    writer.writerows(rows)

conn.close()
print(f"Exported {len(rows)} rows to {csv_path}")