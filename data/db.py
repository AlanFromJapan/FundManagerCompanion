import csv
import sqlite3
import os

csv_path = "import-data-fixed.csv"
db_path = "data.db"


def str2int(s:str):
    """Convert string to integer, handling empty strings."""
    if not s.strip():
        return 0
    s = s.strip().replace(',', '')  # Remove commas
    return int(s) if s.isdigit() else 0


# Create SQLite DB and table
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS "XACT" (
ID INTEGER PRIMARY KEY AUTOINCREMENT,
TradeDate TEXT,
ExecutionDate TEXT,
XactType TEXT,
FundId INTEGER,
Unit INTEGER,
UnitPrice INTEGER,
XactPrice INTEGER,
Currency TEXT DEFAULT "JPY"
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS "FUND" (
FundID INTEGER PRIMARY KEY AUTOINCREMENT,
Name TEXT,
Currency TEXT)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS "FUND_CODE" (
FundID INTEGER,
System TEXT,
Code TEXT,
PRIMARY KEY (FundID, System)
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS "FUND_NAV" (
FundID INTEGER,
AtDate TEXT,
Currency TEXT DEFAULT "JPY",
NAV FLOAT,
PRIMARY KEY (FundID, AtDate, Currency)
)
''')



# Read CSV and get headers
with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=';', quotechar='"')
    _ = next(reader)
    rows = [row for row in reader if any(field.strip() for field in row)]

#---------------------------------------------------------------------------
#The funds
funds = {}
for row in rows:
    fund_id = str(row[5]).strip()
    #fund_id not empty and is a digit 
    if not "" == fund_id and fund_id.isdigit():   
        if fund_id not in funds:
            funds[fund_id] = {
                'Name': str(row[6]),
                'Currency': "JPY",
                'Code': str(row[5])
            }

# Insert data
cnt = 0
for fund in funds.values():
    cur.execute("Select count() from FUND where Name = ? and Currency = ?", (fund['Name'], fund['Currency']))
    if cur.fetchone()[0] > 0:
        continue  # Skip if fund already exists

    cur.execute(
        'INSERT INTO "FUND" (Name, Currency) VALUES (?, ?)',
        (fund['Name'], fund['Currency'])
    )
    fund_id = cur.lastrowid
    cur.execute(
        'INSERT INTO "FUND_CODE" (FundID, System, Code) VALUES (?, ?, ?)',
        (fund_id, "meigara_kodo", fund['Code'])
    )
    cnt += 1
print(f"Inserted {cnt} rows into {db_path} (FUND)")


#---------------------------------------------------------------------------
# The transactions
cnt = 0
for row in rows:
    fund_id = str(row[5]).strip()
    if not "" == fund_id and fund_id.isdigit():
        cur.execute("SELECT FundID FROM FUND_CODE WHERE System = 'meigara_kodo' AND Code = ?", (fund_id,))
        fund_id = cur.fetchone()
        if fund_id is None:
            print("△ WARNING ! Unmatched fund with code:", fund_id)
            print("Row data:", row)
            continue  # Skip if fund does not exist

        fund_id = str(fund_id[0])

        cur.execute(
            'INSERT INTO "XACT" (TradeDate, ExecutionDate, XactType, FundId, Unit, UnitPrice, XactPrice) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                str(row[0]),
                str(row[1]),
                str(row[4]),
                fund_id,
                str2int(row[7]),
                str2int(row[8]),
                max(str2int(row[11]), str2int(row[12]))
            )
        )
        cnt += 1    

print(f"Inserted {cnt} rows into {db_path} (XACT)")




#---------------------------------------------------------------------------
# Transcoding
with open("transcoding.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    _ = next(reader)
    rows = [row for row in reader if any(field.strip() for field in row)]

# Insert transcoding data
cnt = 0
for row in rows:
    fund_id = str2int(row[0].strip())
    if fund_id > 0:
        system = str(row[1]).strip()
        code = str(row[2]).strip()
        cur.execute(
            'INSERT OR IGNORE INTO "FUND_CODE" (FundID, System, Code) VALUES (?, ?, ?)',
            (fund_id, system, code)
        )
        cnt += 1

print(f"Inserted {cnt} rows into {db_path} (FUND_CODE)")

conn.commit()
conn.close()

