from flask import  render_template, request, Blueprint
from shared import get_holdings

bp_holdings = Blueprint('bp_holdings', __name__)

@bp_holdings.route('/holdings', methods=['GET', 'POST'])
def holdings_page():
    pos = get_holdings()
    return render_template('holdings.html', pos=pos)