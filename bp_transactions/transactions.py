
from flask import render_template, request, Blueprint, redirect, url_for, flash
from shared import get_transactions, get_all_funds
import sqlite3
from config import conf

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
    reception_date = request.form.get('reception_date')
    quantity = int(request.form.get('quantity'))
    price = int(request.form.get('price'))
    unitprice = 10000 * price // quantity if quantity and float(quantity) != 0 else 0
    if not fund_id or not reception_date or not quantity or not price:
        flash('All fields are required.', 'error')
        return redirect(url_for('bp_transactions.register_transaction_form'))
    try:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        cur.execute('INSERT INTO XACT (TradeDate, ExecutionDate, XactType, FundID, Unit, XactPrice, UnitPrice) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (reception_date, reception_date, 'お買付', fund_id, quantity, price, unitprice))
        conn.commit()
        conn.close()  
        flash('Transaction registered successfully.', 'success')
    except Exception as e:
        flash(f'Error registering transaction: {e}', 'error')
    return redirect(url_for('bp_transactions.transactions_page'))