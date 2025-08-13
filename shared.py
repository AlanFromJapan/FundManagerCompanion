import csv
from datetime import datetime
import io
from flask import Flask, render_template, request, flash, current_app
import sqlite3

import requests
from fund import Fund
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()


def _save_nav(fund: Fund, date, price, cur: sqlite3.Cursor = None):
    """ Save the NAV for a fund to the database.
    If cur is None, it will use create a dedicated connection + commit.
    """

    if date is None or price is None:
        raise ValueError("Date and price must not be None")

    if date > datetime.now().today():
        print(f"IGNORING FUTURE DATE NAV {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}")
        return

    local_cursor = False
    if cur is None:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        local_cursor = True

    cur.execute("INSERT OR REPLACE INTO FUND_NAV (FundID, AtDate, NAV) VALUES (?, ?, ?)",
                (fund.fund_id, date, price))  # Initialize with None values

    if local_cursor:
        conn.commit()
        conn.close()



def _save_dividend(fund: Fund, date, amount, accounting_period, cur: sqlite3.Cursor = None):
    """ Save the dividend for a fund to the database.
    If cur is None, it will use create a dedicated connection + commit.
    """
    local_cursor = False
    if cur is None:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        local_cursor = True

    cur.execute("INSERT OR REPLACE INTO DIVIDEND (FundID, AtDate, Amount, AccountingPeriod) VALUES (?, ?, ?, ?)",
                (fund.fund_id, date, amount, accounting_period))  # Initialize with None values

    if local_cursor:
        conn.commit()
        conn.close()


def import_latest_nav(fund):
    if isinstance(fund, Fund):
        print(f"Importing NAV for fund {fund.fund_id} ({fund.name})")
        date, price = nav_provider.get_latest_nav(fund)
        print(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}")

        if date is None or price is None:
            flash(f"Failed to fetch NAV for fund {fund.fund_id} ({fund.name})", "error")
            return
        
        flash(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}", "info")

        _save_nav(fund, date, price)
    else:
        if isinstance(fund, list):
            for f in fund:
                print(f"Importing NAV for fund {f.fund_id} ({f.name})")
                import_latest_nav(f)
        else:
            raise ValueError("Invalid fund type. Expected Fund or list of Funds.")



def import_history_nav(fund):
    if isinstance(fund, Fund):
        print(f"Importing History NAV for fund {fund.fund_id} ({fund.name})")

        # Fetch historical NAVs
        history_nav = nav_provider.get_history_nav(fund)
        if history_nav is None or not history_nav or len(history_nav) == 0:
            flash(f"Failed to fetch NAV for fund {fund.fund_id} ({fund.name})", "error")
            return
        
        flash(f"Fetched {len(history_nav)} historical NAVs for fund {fund.fund_id} ({fund.name})", "info")
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        
        for date, price in history_nav.items():
            print(f"Date: {date.strftime('%Y-%m-%d')}, NAV: {price}")

            _save_nav(fund, date, price, cur)

        conn.commit()
        conn.close()
    else:
        if isinstance(fund, list):
            for f in fund:
                print(f"Importing History NAV for fund {f.fund_id} ({f.name})")
                import_history_nav(f)
        else:
            raise ValueError("Invalid fund type. Expected Fund or list of Funds.")




def import_whole_nav(fund):
    """
    Import the whole NAV for the fund from the Investment Trust Association.
    This function should handle the logic to fetch and update the NAV data.
    """
    if isinstance(fund, list):
        # If a list of funds is provided, iterate through each fund
        for f in fund:
            print(f"Importing Whole NAV for fund {f.fund_id} ({f.name})")
            import_whole_nav(f)
        return

    try:
        URL_ITA = "https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000/csv-file-download?isinCd={isin}&associFundCd={id}"
        # Placeholder for actual implementation
        # This should include fetching data from the IITA and updating the fund's NAV
        print(f"Importing whole NAV for fund: {fund.fund_id}")
        # Example: fund.update_nav_from_iita()
        url = URL_ITA.format(isin=fund.codes["ISIN"], id=fund.codes["yahoo_finance"] if fund.codes.get("toushinkyokai") is None else fund.codes.get("toushinkyokai"))
        print(f"Fetching NAV from URL: {url}")
        # Here you would implement the logic to fetch the CSV from the URL and update the fund
        response = requests.get(url)
        response.raise_for_status()
        response_raw = response.text
        response_decoded = response_raw.encode('utf-8').decode('utf-8-sig')  # Handle BOM if present
        csv_data = io.StringIO(response_decoded)
        # Now csv_data can be used to read the CSV content in memory
        reader = csv.reader(csv_data, delimiter=',')
        cnt = 0
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        for row in reader:
            if cnt == 0:
                # Skip header row
                cnt += 1
                continue
            cnt += 1
            nav_date = datetime.strptime(row[0].strip(), "%Y年%m月%d日")
            nav = int(row[1].strip())
            _ = int(row[2].strip()) if len(row) > 2 else None #AUM
            dividend = row[3].strip() if len(row) > 3 else None
            accounting_period = row[4].strip() if len(row) > 4 else None
            _save_nav(fund, nav_date, nav, cur)
            if dividend is not None and accounting_period is not None and dividend != "":
                _save_dividend(fund, nav_date, dividend, accounting_period, cur)

        conn.commit()
        conn.close()
        print(f"Total rows processed: {cnt}")
        flash(f"Imported {cnt} NAV records for fund {fund.fund_id} ({fund.name})", "info")
    except Exception as e:
        print(f"Error importing whole NAV for fund {fund.fund_id} ({fund.name}): {e}")
        flash(f"Failed to import whole NAV for fund {fund.fund_id} ({fund.name}): see logs for details {e}", "error")


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
    F.FundID, 
    F.Name, 
    F.Currency, 
    P.Unit as LatestUnit, 
    P.AtDate as LatestDateHolding, 
    NAVS.NAV as LatestNAV, 
    NAVS.AtDate as LatestDateNAV, 
    NAV_JAN1.NAV as NAV_JAN1,
	((NAVS.NAV - NAV_JAN1.NAV) / NULLIF(NAV_JAN1.NAV, 0)) * 100.0 as YtDPerf
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

	LEFT OUTER JOIN (
    SELECT N.FundId, N.AtDate, N.NAV as NAV
    from FUND_NAV as N
    WHERE
    1=1
	AND N.AtDate >= date('now', 'start of year')
	GROUP BY N.FundId
	) as NAV_JAN1 ON NAV_JAN1.FundId = F.FundId
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
        nav_jan1 = row[7]
        ytd_perf = row[8]

        pos.append({
            'fund_id': fund_id,
            'name': name,
            'currency': currency,
            'latest_unit': latest_unit,
            'latest_date_position': latest_date_position,
            'latest_nav': latest_nav,
            'latest_date_nav': latest_date_nav,
            'nav_jan1': nav_jan1,
            'ytd_perf': ytd_perf
        })
        
    conn.close()

    return pos


def get_transactions(fund_id):
    raise NotImplementedError("This function is not implemented yet. Please implement it in the future.")