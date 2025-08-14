from flask import  render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav, import_whole_nav

bp_transactions = Blueprint('bp_transactions', __name__)

@bp_transactions.route('/transactions', methods=['GET', 'POST'])
def transactions_page():
    return render_template('transactions.html')