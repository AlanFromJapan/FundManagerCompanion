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
    
    cur.execute('SELECT FundID, Name, Currency FROM FUND')
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

