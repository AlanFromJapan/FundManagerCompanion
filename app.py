from flask import Flask, render_template, request
from config import conf 

from nav.yahoo_fin_provider import YahooFinProvider
nav_provider = YahooFinProvider()

from shared import get_all_funds, import_latest_nav, get_latest_positions
from bp_fund_detail.fund_detail import bp_fund_details

app = Flask(__name__)
app.secret_key = conf['SECRET_KEY']

#Register the blueprints
app.register_blueprint(bp_fund_details)


@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')


@app.route('/funds', methods=['GET','POST'])
def show_funds_page():
    pos = get_latest_positions()
    funds = get_all_funds()

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        print("POST request received")
        if 'update_nav' in request.form:
            print("Updating NAV for all funds")
            for fund in funds:
                import_latest_nav(fund)

    return render_template('funds.html', pos=pos, funds=funds)







if __name__ == '__main__':
    app.run(debug=True)
