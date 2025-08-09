from flask import  render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav, import_whole_nav

bp_fund_details = Blueprint('bp_fund_details', __name__)



@bp_fund_details.route('/funds/<int:fund_id>', methods=['GET','POST'])
def show_fund_page(fund_id):
    MAX_NAV_LIMIT = 300  # Limit for NAV records to fetch
    MAX_NAV_SHOWN = 100  # Limit for NAV records to show in the chart

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
        elif 'update_whole_nav' in request.form:
            import_whole_nav(fund)

    # Fetch latest known NAV for the fund from DB
    fund.get_fund_nav(MAX_NAV_LIMIT)

    # Prepare data for the chart
    if fund.nav:
        #reverse the nav_sorted to have oldest first (L to R)
        #show the last 100 NAVs
        snav = fund.nav_sorted[:MAX_NAV_SHOWN]
        snav.reverse()  # Reverse to have oldest first

        values = [{'x': date, 'y': int(nav)} for date, nav in snav]
        labels = [date[:10] for date, _ in snav]


    return render_template('fund_detail.html', fund=fund, chartData=(values, labels, MAX_NAV_LIMIT, MAX_NAV_SHOWN))