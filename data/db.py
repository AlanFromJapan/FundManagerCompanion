import csv
import sqlite3
import os
import datetime

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

cur.execute('''
CREATE TABLE IF NOT EXISTS "POSITION" (
FundID INTEGER,
AtDate TEXT,
Unit INTEGER,
Amount INTEGER,
Currency TEXT DEFAULT "JPY",
PRIMARY KEY (FundID, AtDate)
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS "DIVIDEND" (
FundID INTEGER,
AtDate TEXT,
Amount INTEGER,
AccountingPeriod INTEGER,
PRIMARY KEY (FundID, AtDate)
)
''')

#---------------------------------------------------------------------------
# Offset the positions (could retrieve only transactions past jan 2022)
# Read CSV and get headers
with open("initiale_position_adjust.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=';', quotechar='"')
    _ = next(reader)
    rows = [row for row in reader if any(field.strip() for field in row)]

#offset the positions
offsets = {}
for row in rows:
    fund_id = str(row[0]).strip()
    adjust = int(row[4])
    if not "" == fund_id and fund_id.isdigit() and adjust != 0:
        fund_id = int(fund_id)
        offsets[fund_id] = adjust


#---------------------------------------------------------------------------


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
cur.execute("DELETE FROM XACT")  # Clear existing transactions
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
                datetime.datetime.strptime(str(row[0]), '%Y/%m/%d').strftime('%Y-%m-%d'),
                datetime.datetime.strptime(str(row[1]), '%Y/%m/%d').strftime('%Y-%m-%d'),
                str(row[4]).strip(),
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


#---------------------------------------------------------------------------
# Positions calculation

cur.execute("SELECT * FROM XACT ORDER BY TradeDate ASC")
row = cur.fetchone()
exec_date = row[2]
exec_date = datetime.datetime.strptime(exec_date, '%Y-%m-%d')
print("Minimal execution date:", exec_date.strftime('%Y-%m-%d'))
previous_exec_date = exec_date - datetime.timedelta(days=1)
print("Previous execution date:", previous_exec_date.strftime('%Y-%m-%d'))

print("Seeding initial positions...")
cur.execute("DELETE FROM POSITION")  # Clear existing positions
cur.execute(
    '''INSERT OR REPLACE INTO "POSITION" (FundID, AtDate, Unit, Amount) 
Select FundId, ?, 0, 0 FROM FUND''',
    (previous_exec_date.strftime('%Y-%m-%d'),)
)

#offsets the positions
for fund_id, adjust in offsets.items():
    cur.execute(
        'UPDATE POSITION SET Unit = ? WHERE FundID = ?',
        (adjust, fund_id,)
    )
    print(f"Offsetting fund {fund_id} by {adjust} units")


cnt = 0
#get all the transactions
cur.execute("SELECT * FROM XACT ORDER BY ExecutionDate ASC")
xacts = cur.fetchall()
d = exec_date
#for every date until yesterday
while d <= datetime.datetime.today() - datetime.timedelta(days=1):
    # copy the previous day's positions
    cur.execute(
        '''INSERT OR REPLACE INTO "POSITION" (FundID, AtDate, Unit, Amount) 
        SELECT FundID, ?, Unit, Amount FROM POSITION WHERE AtDate = ?''',
        (d.strftime('%Y-%m-%d'), (d - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
    )

    #print(f"▶Processing positions for date: {d.strftime('%Y-%m-%d')} len(xacts)={len(xacts)}")

    # Process transactions for the current date (d = execution date)
    while len(xacts) > 0 and xacts[0][2] == d.strftime('%Y-%m-%d'):
        print("Processing transactions for date:", d.strftime('%Y-%m-%d'))
        row = xacts.pop(0)

        # Process the transaction
        fund_id = row[4]
        exec_date = row[2]
        unit = row[5]
        xact_type = row[3]
        amount = row[6] * unit  # XactPrice is the total price for the units

        if xact_type == 'お買付':
            #buy
            pass
        elif xact_type == '再投資買付':
            #reinvestment buy
            pass
        elif xact_type == '解約':
            #sell (redemption)
            unit = -unit
            amount = -amount
        else:
            #skip other types (e.g. dividends, etc.)
            continue

        print(f"Processing transaction: {xact_type} {unit} units at {amount} each for fund {fund_id} on {exec_date} ")
        # Update the position
        cur.execute(
            #TODO FIX don't sum amount, recalculate it with NAV of the date once I have it (future update)
            'UPDATE POSITION SET Unit = Unit + ?, Amount = Amount + ? WHERE FundID = ? AND AtDate = ?',
            (unit, amount, fund_id, d.strftime('%Y-%m-%d'))
        )




    #next day
    d = d + datetime.timedelta(days=1)
    cnt += 1

print(f"Inserted {cnt} rows into {db_path} (POSITION)")



conn.commit()
conn.close()

