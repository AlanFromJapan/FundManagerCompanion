import csv
from datetime import datetime
import io
from flask import Flask, render_template, request, flash, current_app
import sqlite3

import requests
from fund import Fund, TransactionType
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
from nav.toushinkyokai_provider import toshinkyokai_provider
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
        
        flash(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}", "success")

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
        history_nav, _ = nav_provider.get_history_nav(fund)
        if history_nav is None or not history_nav or len(history_nav) == 0:
            flash(f"Failed to fetch NAV for fund {fund.fund_id} ({fund.name})", "error")
            return
        
        flash(f"Fetched {len(history_nav)} historical NAVs for fund {fund.fund_id} ({fund.name})", "success")
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
        cnt = 0
        cntd = 0

        nav_dict, div_dict = toshinkyokai_provider().get_history_nav(fund)

        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()


        if nav_dict:
            for date, nav_price in nav_dict.items():
                _save_nav(fund, date, nav_price, cur)
                cnt += 1
        
        if div_dict:
            for date, (dividend, accounting_period) in div_dict.items():
                _save_dividend(fund, date, dividend, accounting_period, cur)
                cntd += 1


        conn.commit()
        conn.close()

        print(f"Total NAV/Div processed: {cnt}/{cntd}")
        flash(f"Imported {cnt} NAV & {cntd} Dividend records for fund {fund.fund_id} ({fund.name})", "success")
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

    cur.execute('SELECT F.FundID, F.Name, F.Currency, COALESCE(P.Unit, 0) as LatestUnit, COALESCE(P.AtDate, date("now")) as LatestDate from FUND as F LEFT OUTER JOIN POSITION as P ON F.FundId = P.FundId AND P.AtDate = (SELECT MAX(P2.AtDate) FROM POSITION as P2)')
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
    NAV_6M.NAV as NAV_6M,
	((NAVS.NAV - NAV_6M.NAV) / NULLIF(NAV_6M.NAV, 0)) * 100.0 as Perf6M,
	((NAVS.NAV - NAV_6M.NAV + COALESCE((SELECT SUM(D.Amount) from DIVIDEND as D WHERE D.FundID = F.FundID AND D.AtDate >= date('now', '-6 months')), 0)) / NULLIF(NAV_6M.NAV, 0)) * 100.0 as TotalReturn6M,
    CAST((NAVS.NAV * P.Unit) /10000 as INTEGER) as LatestPosition,
	((NAVS.NAV - NAV_12M.NAV) / NULLIF(NAV_12M.NAV, 0)) * 100.0 as Perf12M,
	((NAVS.NAV - NAV_12M.NAV + COALESCE((SELECT SUM(D.Amount) from DIVIDEND as D WHERE D.FundID = F.FundID AND D.AtDate >= date('now', '-12 months')), 0)) / NULLIF(NAV_12M.NAV, 0)) * 100.0 as TotalReturn12M
                
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
	AND N.AtDate >= date('now', '-6 months')
	GROUP BY N.FundId
	) as NAV_6M ON NAV_6M.FundId = F.FundId
                
	LEFT OUTER JOIN (
    SELECT N.FundId, N.AtDate, N.NAV as NAV
    from FUND_NAV as N
    WHERE
    1=1
	AND N.AtDate >= date('now', '-12 months')
	GROUP BY N.FundId
	) as NAV_12M ON NAV_12M.FundId = F.FundId                
WHERE
    1=1    
    --AND P.Unit > 0	
                
""")

    rows = cur.fetchall()
    total_holdings_amt = 0
    for row in rows:
        total_holdings_amt += row[3] * row[5] / 10000.0

    for row in rows:
        fund_id = row[0]
        name = row[1]
        currency = row[2]
        latest_unit = row[3]
        latest_date_position = row[4]
        latest_nav = row[5]
        latest_date_nav = row[6]
        nav_jan1 = row[7]
        perf_6m = row[8]
        total_return_6m = row[9]
        latest_position = row[10]
        perf_12m = row[11]
        total_return_12m = row[12]

        pos.append({
            'fund_id': fund_id,
            'name': name,
            'currency': currency,
            'latest_unit': latest_unit,
            'latest_date_position': latest_date_position,
            'latest_nav': latest_nav,
            'latest_date_nav': latest_date_nav,
            'nav_jan1': nav_jan1,
            'perf_6m': perf_6m,
            'total_return_6m': total_return_6m,
            'latest_position': latest_position,
            'portfolio_holding_contrib_pct': int(latest_position / total_holdings_amt * 100.0) if total_holdings_amt > 0 else 0,
            'perf_12m': perf_12m,
            'total_return_12m': total_return_12m,
            'perf_evolution': perf_12m - perf_6m if perf_12m is not None and perf_6m is not None else 0.0
        })
        
    conn.close()

    return pos




def get_transactions(fund_id: int = None):
    return Fund.get_all_transactions(fund_id)



def get_holdings(fund_id: int = None, limit :int = 100):
    pos = []
    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()

    cur.execute("""
    select 
                P.FundId, 
                P.AtDate, 
                P.Unit, 
                P.Amount, 
                F.Name as FundName
    from 
                Position as P JOIN FUND as F ON P.FundID = F.FundID 
    WHERE 
                1=1
                AND (P.FundID = ? OR ? IS NULL)                
    order by P.AtDate DESC LIMIT ?""", (fund_id, fund_id, limit))

    rows = cur.fetchall()
    for row in rows:
        pos.append({
            'fund_id': row[0],
            'at_date': row[1],
            'unit': row[2],
            'amount': row[3],
            'fund_name': row[4]
        })
    conn.close()
    return pos



def get_coding_systems():
    ''' Get all distinct coding systems from FUND_CODE table '''
    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT System FROM FUND_CODE")
    rows = cur.fetchall()
    conn.close()
    return rows