

import os
from flask import Flask, render_template, request, send_from_directory
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()

from shared import get_all_funds, import_latest_nav, get_latest_positions, import_history_nav, import_whole_nav, get_holdings_eom_sum, get_investments_eom, get_overall_stats

from bp_fund_detail.fund_detail import bp_fund_details
from bp_admin.admin import bp_admin
from bp_transactions.transactions import bp_transactions
from bp_holdings.holdings import bp_holdings
from bp_newfund import bp_newfund
from bp_api.api import bp_api
from bp_analysis.analysis import bp_analysis

app = Flask(__name__, static_url_path='')
app.secret_key = conf['SECRET_KEY']
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000  # Max upload - 16 MB


#Register the blueprints

app.register_blueprint(bp_fund_details)
app.register_blueprint(bp_admin)
app.register_blueprint(bp_transactions)
app.register_blueprint(bp_holdings)
app.register_blueprint(bp_newfund)
app.register_blueprint(bp_api)
app.register_blueprint(bp_analysis)


@app.context_processor
def inject_extra_context():
    #For ALL the templates to have access to some common values
    return dict(isProd=os.environ.get('FLASK_ENV','') == 'prod')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')

@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')


@app.route('/funds', methods=['GET','POST'])
def show_funds_page():
    eom_months_display = 24  #how many months to display in the EOM chart

    pos = get_latest_positions()
    funds = get_all_funds()

    eom_sum = get_holdings_eom_sum(limit=eom_months_display)
    inv_eom = get_investments_eom(limit=eom_months_display)

    stats = get_overall_stats()

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

    return render_template('funds.html', pos=pos, funds=funds, stats=stats, conf=conf, eom=eom_sum, inv=inv_eom)






if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
