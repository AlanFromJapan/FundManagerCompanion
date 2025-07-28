from flask import Flask, render_template, request, flash, current_app
import sqlite3
from fund import Fund
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()


def import_latest_nav(fund):
    if isinstance(fund, Fund):
        print(f"Importing NAV for fund {fund.fund_id} ({fund.name})")
        date, price = nav_provider.get_latest_nav(fund)
        print(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}")

        if date is None or price is None:
            flash(f"Failed to fetch NAV for fund {fund.fund_id} ({fund.name})", "error")
            return
        
        flash(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}", "info")

        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("INSERT OR IGNORE INTO FUND_NAV (FundID, AtDate, NAV) VALUES (?, ?, ?)",
                    (fund.fund_id, date, price))  # Initialize with None values
        conn.commit()
        conn.close()
    else:
        if isinstance(fund, list):
            for f in fund:
                print(f"Importing NAV for fund {f.fund_id} ({f.name})")
                import_latest_nav(f)
        else:
            raise Exception("Invalid fund type. Expected Fund or list of Funds.")


__funds = None
def get_all_funds(forced_reload=False):
    global __funds
    if __funds is not None and not forced_reload:
        return __funds

    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()
    
    cur.execute('SELECT F.FundID, F.Name, F.Currency, P.Unit as LatestUnit, P.AtDate as LatestDate from FUND as F JOIN POSITION as P ON F.FundId = P.FundId AND P.AtDate = (SELECT MAX(P2.AtDate) FROM POSITION as P2)')
    rows = cur.fetchall()

    #ugly but not so many funs that it counts
    cur.execute("SELECT * FROM FUND_CODE")
    codes = cur.fetchall()

    conn.close()

    __funds = [Fund.from_db_row(row) for row in rows]

    for fund in __funds:
        for code in codes:
            if fund.fund_id == code[0]:
                fund.codes[code[1]] = code[2]  # Assuming code[1] is the system and code[2] is the value


    return __funds


def get_latest_positions():
    pos = []
    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()
    
    cur.execute("""
SELECT 
    F.FundID, F.Name, F.Currency, P.Unit as LatestUnit, P.AtDate as LatestDateHolding, NAVS.NAV as LatestNAV, NAVS.AtDate as LatestDateNAV
from 
    FUND as F 
    JOIN POSITION as P ON F.FundId = P.FundId AND P.AtDate = (SELECT MAX(P2.AtDate) FROM POSITION as P2)

    JOIN (
    SELECT N.FundId, N.AtDate, N.NAV as NAV
    from FUND_NAV as N
    WHERE
    1=1
    GROUP BY N.FundId having N.AtDate = Max(N.AtDate)
    ) as NAVS ON F.FundId = NAVS.FundId
WHERE
    1=1
    AND P.Unit > 0
                
""")

    rows = cur.fetchall()
    for row in rows:
        fund_id = row[0]
        name = row[1]
        currency = row[2]
        latest_unit = row[3]
        latest_date_position = row[4]
        latest_nav = row[5]
        latest_date_nav = row[6]

        pos.append({
            'fund_id': fund_id,
            'name': name,
            'currency': currency,
            'latest_unit': latest_unit,
            'latest_date_position': latest_date_position,
            'latest_nav': latest_nav,
            'latest_date_nav': latest_date_nav
        })
        
    conn.close()

    return pos
