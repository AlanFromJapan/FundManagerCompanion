from flask import  flash, render_template, request, Blueprint, send_file, redirect, url_for
from shared import get_all_funds
from datetime import datetime
from fund import Fund

from config import conf

bp_analysis = Blueprint('bp_analysis', __name__)

@bp_analysis.route('/analysis', methods=['GET'])
def analysis_page():
    funds = get_all_funds()
    
    
    for fund in funds:
        fund.get_fund_nav(5)  # Fetch only the latest NAV for each fund
    
    # Filter out funds without holdings
    funds = [f for f in funds if f.latest_units > 0]

    #sort by 1Y return, with those missing the stat at the bottom
    funds = sorted(funds, key=lambda f: f.stats["return_1y"] if "return_1y" in f.stats else float('-inf'), reverse=True) 

    return render_template('analysis.html', funds=funds, conf=conf)