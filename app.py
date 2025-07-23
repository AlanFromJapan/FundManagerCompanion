from flask import Flask, render_template, request
import sqlite3
from fund import Fund
from config import conf
from pychartjs import BaseChart, ChartType, Color      

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()



app = Flask(__name__)


class MyBarGraph(BaseChart):

    type = ChartType.Bar

    class data:
        label = "Numbers"
        type = ChartType.Line
        data = [12, 19, 3, 17, 10]
        backgroundColor = Color.Green


@app.route('/')
@app.route('/home')
def home_page():
    NewChart = MyBarGraph()
    NewChart.data.label = "My Favourite Numbers"      # can change data after creation

    ChartJSON = NewChart.get()

    return render_template('home.html', chartJSON=ChartJSON)


@app.route('/funds', methods=['GET','POST'])
def show_funds_page():
    funds = get_all_funds()

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        print("POST request received")
        if 'update_nav' in request.form:
            print("Updating NAV for all funds")
            for fund in funds:
                import_latest_nav(fund)

    return render_template('funds.html', funds=funds)


@app.route('/funds/<int:fund_id>', methods=['GET','POST'])
def show_fund_page(fund_id):
    funds = get_all_funds()
    fund = next((f for f in funds if f.fund_id == fund_id), None)
    if fund is None:
        return "Fund not found", 404

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        if 'update_nav' in request.form:
            import_latest_nav(fund)

    # Fetch latest known NAV for the fund from DB
    fund.get_fund_nav()

    return render_template('fund_detail.html', fund=fund)




def import_latest_nav(fund):
    if isinstance(fund, Fund):
        print(f"Importing NAV for fund {fund.fund_id} ({fund.name})")
        date, price = nav_provider.get_latest_nav(fund)
        print(f"Latest NAV for fund {fund.fund_id} ({fund.name}): Date: {date}, Price: {price}")

        if date is None or price is None:
            print(f"Failed to fetch NAV for fund {fund.fund_id} ({fund.name})")
            return
        
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


if __name__ == '__main__':
    app.run(debug=True)
