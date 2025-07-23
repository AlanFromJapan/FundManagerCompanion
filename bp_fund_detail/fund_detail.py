
from pychartjs import BaseChart, ChartType, Color     
from flask import  render_template, request, Blueprint


from shared import get_all_funds, import_latest_nav

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

    # Fetch latest known NAV for the fund from DB
    fund.get_fund_nav()

    NewChart = NavChart()
    NewChart.data.label = fund.name
    NewChart.data.data = [x[1] for x in fund.nav_sorted] if fund else []

    ChartJSON = NewChart.get()

    return render_template('fund_detail.html', fund=fund, chartJSON=ChartJSON)