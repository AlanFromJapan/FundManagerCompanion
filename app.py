from flask import Flask, render_template
import sqlite3
from fund import Fund

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

def get_all_funds():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('SELECT FundID, Name, Currency FROM FUND')
    rows = cur.fetchall()

    #ugly but not so many funs that it counts
    cur.execute("SELECT * FROM FUND_CODE")
    codes = cur.fetchall()

    conn.close()

    funds = [Fund.from_db_row(row) for row in rows]

    for fund in funds:
        for code in codes:
            if fund.fund_id == code[0]:
                fund.codes[code[1]] = code[2]  # Assuming code[1] is the system and code[2] is the value


    return funds

if __name__ == '__main__':
    app.run(debug=True)
