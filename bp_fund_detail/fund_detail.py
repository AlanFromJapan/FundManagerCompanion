from flask import  render_template, request, Blueprint, session
from shared import get_all_funds, import_latest_nav, import_history_nav, import_whole_nav
from config import conf

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

    # Get dividends
    fund.get_dividends()

    # Get transactions
    fund.get_transactions()

    # Prepare data for the chart
    if fund.nav:
        #reverse the nav_sorted to have oldest first (L to R)
        #show the last 100 NAVs
        snav = fund.nav_sorted[:MAX_NAV_SHOWN]
        snav.reverse()  # Reverse to have oldest first

        values = [{'x': date, 'y': int(nav)} for date, nav in snav]
        labels = [date[:10] for date, _ in snav]




    return render_template('fund_detail.html', fund=fund, chartData=(values, labels, MAX_NAV_LIMIT, MAX_NAV_SHOWN), conf=conf, prevnext=get_prev_next_fund(fund.fund_id))


def get_prev_next_fund( current_fund_id):
    pos = session.get('latest_positions', [])
    fund_ids = [f["fund_id"] for f in pos]

    if current_fund_id not in fund_ids:
        return None, None
    idx = fund_ids.index(current_fund_id)
    prev_fund = pos[idx - 1] if idx > 0 else pos[-1]
    next_fund = pos[idx + 1] if idx < len(pos) - 1 else pos[0]
    return prev_fund["fund_id"] , next_fund["fund_id"]