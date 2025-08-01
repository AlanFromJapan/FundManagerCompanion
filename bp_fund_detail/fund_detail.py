
from html import parser
from pychartjs import BaseChart, ChartType, Color     
from flask import  render_template, request, Blueprint


from shared import get_all_funds, import_latest_nav, import_history_nav

bp_fund_details = Blueprint('bp_fund_details', __name__)

class NavChart(BaseChart):

    type = ChartType.Bar

    class data:
        label = "NAV"
        type = ChartType.Line
        borderColor = Color.Green
    
    class options:
        scales = {
            'yAxes': [{
                'ticks': {
                    'beginAtZero': True
                }
            }],
            'xAxes': [{
                #'type': 'time',
                'time': {
                    'parser': 'YYYY-MM-DD HH:mm:ss',
                    'unit': 'day',
                    'tooltipFormat': 'll'
                },
            }]
        }


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
        NewChart = NavChart()
        NewChart.data.label = fund.name

        # NewChart.data.data = [x[1] for x in fund.nav_sorted] if fund else []
        NewChart.data.data = []
        #reverse the nav_sorted to have oldest first (L to R)
        snav = fund.nav_sorted
        snav.reverse()  # Reverse to have oldest first
        for date, nav in snav:
            NewChart.data.data.append({'x': date, 'y': nav})

        ChartJSON = NewChart.get()
    else:
        ChartJSON = None

    return render_template('fund_detail.html', fund=fund, chartJSON=ChartJSON)