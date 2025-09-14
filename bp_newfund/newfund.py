from flask import Blueprint, request, flash, redirect, url_for, render_template
import sqlite3
from config import conf
from shared import get_coding_systems

bp_newfund = Blueprint('bp_newfund', __name__)

@bp_newfund.route('/funds/register', methods=['GET'])
def register_fund_form():
    codingsys = get_coding_systems()

    return render_template('register_fund.html', coding_systems=codingsys)

#For the POST method
@bp_newfund.route('/funds/register', methods=['POST'])
def register_fund():
    name = request.form.get('name')
    currency = request.form.get('currency')
    if not name or not name.strip():
        flash('Fund name cannot be empty.', 'error')
        return redirect(url_for('bp_newfund.register_fund_form'))
    if not currency:
        flash('Currency is required to register a fund.', 'error')
        return redirect(url_for('bp_newfund.register_fund_form'))
    

    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()
    try:
        # Check if fund name already exists
        cur.execute('SELECT FundID FROM FUND WHERE Name = ?', (name.strip(),))
        if cur.fetchone():
            flash(f'Fund name "{name}" already exists. Please choose a unique name.', 'error')
            conn.close()
            return redirect(url_for('bp_newfund.register_fund_form'))
        # Insert new fund
        cur.execute('INSERT INTO FUND (Name, Currency) VALUES (?, ?)', (name.strip(), currency.upper()))

        #check that the fund was properly inserted
        cur.execute("SELECT FundID FROM FUND WHERE Name = ? AND Currency = ?", (name.strip(), currency.upper()))
        row = cur.fetchone()
        if row is None:
            flash(f'Error: Fund {name} was not inserted properly.', 'error')
            conn.close()
            return redirect(url_for('bp_newfund.register_fund_form'))
        else:
            fund_id = row[0]

        #register the coding system if provided
        codingsys = get_coding_systems()
        for code in codingsys:
            code_value = request.form.get(f'coding_system_{code[0]}')
            if code_value:
                cur.execute('INSERT INTO FUND_CODE (FundID, System, Code) VALUES (?, ?, ?)', (fund_id, code[0], code_value.strip()))

        #ZA final commit
        conn.commit()

        flash(f'Fund {name} (ID: {fund_id}) registered successfully.', 'success')
    except Exception as e:
        flash(f'Error registering fund: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('show_funds_page'))
