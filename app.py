

from flask import Flask, render_template, request, send_from_directory
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()

from shared import get_all_funds, import_latest_nav, get_latest_positions, import_history_nav, import_whole_nav, get_holdings_eom

from bp_fund_detail.fund_detail import bp_fund_details
from bp_admin.admin import bp_admin
from bp_transactions.transactions import bp_transactions
from bp_holdings.holdings import bp_holdings
from bp_newfund import bp_newfund

app = Flask(__name__, static_url_path='')
app.secret_key = conf['SECRET_KEY']

#Register the blueprints

app.register_blueprint(bp_fund_details)
app.register_blueprint(bp_admin)
app.register_blueprint(bp_transactions)
app.register_blueprint(bp_holdings)
app.register_blueprint(bp_newfund)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')

@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')


@app.route('/funds', methods=['GET','POST'])
def show_funds_page():
    pos = get_latest_positions()
    funds = get_all_funds()
    eom = get_holdings_eom()

    #sum the end of month positions
    eom_sum = {}
    for d in eom:
        eom_sum[d['at_date']] = eom_sum.get(d['at_date'], 0) + d['amount']


    stats = {}
    stats['total_funds_count'] = len(funds)
    stats['total_positions'] = sum(p["latest_unit"] * p["latest_nav"] /10000.0 for p in pos)

    #sort positions ascending by maximum calculated position value
    pos.sort(key=lambda x: x["latest_unit"] * x["latest_nav"], reverse=True)

    #ignore positions with zero qty
    pos = [p for p in pos if p["latest_unit"]  > 0]

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        if 'update_nav' in request.form:
            print("Updating NAV for all funds")
            import_latest_nav(funds)
        elif 'update_history_nav' in request.form:
            print("Updating historical NAV for all funds")
            import_history_nav(funds)
        elif 'update_whole_nav' in request.form:
            print("Updating whole NAV for all funds from Investment Trust Association")
            import_whole_nav(funds)

    return render_template('funds.html', pos=pos, funds=funds, stats=stats, conf=conf, eom=eom_sum)






if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
