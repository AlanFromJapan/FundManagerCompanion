from flask import  render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav
from datetime import datetime

bp_fund_details = Blueprint('bp_fund_details', __name__)


@bp_fund_details.route('/funds/<int:fund_id>', methods=['GET','POST'])
def show_fund_page(fund_id):
    funds = get_all_funds()
    fund = next((f for f in funds if f.fund_id == fund_id), None)
    if fund is None:
        return "Fund not found", 404

    #POST BACK POST BACK POST BACK
    if request.method == 'POST':
        if 'update_nav' in request.form:
            import_latest_nav(fund)
        elif 'update_history_nav' in request.form:
            import_history_nav(fund)

    # Fetch latest known NAV for the fund from DB
    fund.get_fund_nav()

    # Prepare data for the chart
    if fund.nav:
        #reverse the nav_sorted to have oldest first (L to R)
        snav = fund.nav_sorted
        snav.reverse()  # Reverse to have oldest first

        values = [{'x': date, 'y': int(nav)} for date, nav in snav]
        labels = [date[:10] for date, _ in snav]


    return render_template('fund_detail.html', fund=fund, chartData=(values, labels))