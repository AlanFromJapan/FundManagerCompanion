from flask import  render_template, request, Blueprint
from shared import get_transactions

bp_transactions = Blueprint('bp_transactions', __name__)

@bp_transactions.route('/transactions', methods=['GET', 'POST'])
def transactions_page():
    xact = get_transactions()
    return render_template('transactions.html', transactions=xact)