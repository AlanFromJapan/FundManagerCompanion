from flask import Flask, render_template, request
import sqlite3
from fund import Fund

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()


DB_PATH = 'data/data.db'
app = Flask(__name__)

@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')


@app.route('/funds')
def show_funds_page():
    funds = get_all_funds()
    return render_template('funds.html', funds=funds)


@app.route('/funds/<int:fund_id>', methods=['GET','POST'])
def show_fund_page(fund_id):
    funds = get_all_funds()
    fund = next((f for f in funds if f.fund_id == fund_id), None)
    if fund is None:
        return "Fund not found", 404

    # Fetch latest known NAV for the fund from DB
    get_fund_nav(fund)

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        if 'update_nav' in request.form:
            import_latest_nav(fund)
            return render_template('fund_detail.html', fund=fund)

    return render_template('fund_detail.html', fund=fund)


def get_fund_nav(fund:Fund):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT AtDate, NAV FROM FUND_NAV WHERE FundID = ?", (fund.fund_id,))
    row = cur.fetchone()

    conn.close()

    if row is not None:
        fund.nav[row[0]] = float(row[1])


def import_latest_nav(fund):
    if isinstance(fund, Fund):
        date, price = nav_provider.get_latest_nav(fund)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("INSERT OR IGNORE INTO FUND_NAV (FundID, AtDate, NAV) VALUES (?, ?, ?)",
                    (fund.fund_id, date, price))  # Initialize with None values
        conn.commit()
        conn.close()
    else:
        if isinstance(fund, list):
            for f in fund:
                import_latest_nav(f)
        else:
            raise Exception("Invalid fund type. Expected Fund or list of Funds.")


__funds = None
def get_all_funds():
    global __funds
    if __funds is not None:
        return __funds
    
    conn = sqlite3.connect(DB_PATH)
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


if __name__ == '__main__':
    app.run(debug=True)
