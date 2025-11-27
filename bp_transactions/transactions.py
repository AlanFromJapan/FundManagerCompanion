
from flask import render_template, request, Blueprint, redirect, url_for, flash
from shared import get_transactions, get_all_funds, recalculate_positions
import sqlite3
from config import conf
import datetime

bp_transactions = Blueprint('bp_transactions', __name__)


@bp_transactions.route('/transactions', methods=['GET', 'POST'])
def transactions_page():
    xact = get_transactions()
    return render_template('transactions.html', transactions=xact)

@bp_transactions.route('/transactions/register', methods=['GET'])
def register_transaction_form():
    funds = get_all_funds()
    return render_template('register_transaction.html', funds=funds)

@bp_transactions.route('/transactions/register', methods=['POST'])
def register_transaction():    
    fund_id = request.form.get('fund_id')
    trans_type = request.form.get('transaction_type')
    trans_type = 'お買付' if trans_type == 'purchase' else '解約' #Ugly, centralize later
    reception_date = request.form.get('reception_date')
    quantity = abs(int(request.form.get('quantity'))) # Always positive quantity
    amount = abs(int(request.form.get('amount'))) # Always positive amount
    unitprice = round(10000.0 * amount / quantity) if quantity and float(quantity) != 0 else 0
    if not fund_id or not reception_date or not quantity or not amount:
        flash('All fields are required.', 'error')
        return redirect(url_for('bp_transactions.register_transaction_form'))
    try:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        cur.execute('INSERT INTO XACT (TradeDate, ExecutionDate, XactType, FundID, Unit, XactPrice, UnitPrice) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (reception_date, reception_date, trans_type, fund_id, quantity, amount, unitprice))
        conn.commit()
        conn.close()  
        flash('Transaction registered successfully.', 'success')

        # Recalculate positions since the transaction date -1d in case
        start_date = datetime.datetime.strptime(reception_date, '%Y-%m-%d') - datetime.timedelta(days=1)
        recalculate_positions(start_date=start_date, fund_id=int(fund_id))

        flash(f'Positions recalculated successfully since {start_date}.', 'success')

    except Exception as e:
        flash(f'Error registering transaction: {e}', 'error')
    return redirect(url_for('bp_transactions.transactions_page'))