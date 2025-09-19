from flask import render_template, request, Blueprint, redirect, url_for, flash
from shared import get_holdings, recalculate_positions, get_all_funds
import sqlite3
from config import conf
import datetime

bp_holdings = Blueprint('bp_holdings', __name__)


@bp_holdings.route('/holdings', methods=['GET', 'POST'])
def holdings_page():
    pos = get_holdings()
    funds = get_all_funds()
    return render_template('holdings.html', pos=pos, funds=funds)

@bp_holdings.route('/holdings/rerun_position', methods=['POST'])
def rerun_position():

    start_date = request.form.get('start_date') if request.form.get('enable_start_date') else None
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d') if start_date else None

    fund_id = request.form.get('fund_id', "-1") # -1 means all funds
    fund_id = int(fund_id) if fund_id and fund_id != -1 else None
    
    print(f"Rerunning position from {start_date} for fund_id={fund_id}")

    recalculate_positions(start_date=start_date, fund_id=fund_id)

    return redirect(url_for('bp_holdings.holdings_page'))