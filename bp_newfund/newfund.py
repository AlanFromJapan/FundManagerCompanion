from flask import Blueprint, request, flash, redirect, url_for, render_template
import sqlite3
from config import conf

bp_newfund = Blueprint('bp_newfund', __name__)
@bp_newfund.route('/funds/register', methods=['GET'])
def register_fund_form():
    return render_template('register_fund.html')

@bp_newfund.route('/funds/register', methods=['POST'])
def register_fund():
    fund_id = 0
    name = request.form.get('name')
    currency = request.form.get('currency')
    if not name or not currency:
        flash('All fields are required to register a fund.', 'error')
        return redirect(url_for('show_funds_page'))
    try:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        cur.execute('INSERT INTO FUND (Name, Currency) VALUES (?, ?)', (name, currency.upper()))
        conn.commit()

        #check that the fund was properly inserted
        cur.execute("SELECT FundID FROM FUND WHERE Name = ? AND Currency = ?", (name, currency.upper()))
        row = cur.fetchone()
        if row is None:
            flash(f'Error: Fund {name} was not inserted properly.', 'error')
            return redirect(url_for('show_funds_page'))
        else:
            fund_id = row[0]

        conn.close()
        flash(f'Fund {name} (ID: {fund_id}) registered successfully.', 'success')
    except Exception as e:
        flash(f'Error registering fund: {e}', 'error')
    return redirect(url_for('show_funds_page'))
