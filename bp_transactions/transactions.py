
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
        start_date = xact_save_to_db(fund_id, trans_type, reception_date, quantity, amount, unitprice)

        flash(f'Positions recalculated successfully since {start_date}.', 'success')

    except Exception as e:
        flash(f'Error registering transaction: {e}', 'error')
    return redirect(url_for('bp_transactions.transactions_page'))



def xact_save_to_db(fund_id, trans_type, reception_date, quantity, amount, unitprice):
    conn = sqlite3.connect(conf['DB_PATH'])
    cur = conn.cursor()

    # first check if not already exists a transaction with same fund_id, reception_date, quantity
    cur.execute('SELECT COUNT(*) FROM XACT WHERE FundID = ? AND TradeDate = ? AND Unit = ? AND XactType = ?',
                (fund_id, reception_date, quantity, trans_type))
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT OR IGNORE INTO XACT (TradeDate, ExecutionDate, XactType, FundID, Unit, XactPrice, UnitPrice) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (reception_date, reception_date, trans_type, fund_id, quantity, amount, unitprice))
        conn.commit()
        conn.close()  
        flash('Transaction registered successfully.', 'success')

        # Recalculate positions since the transaction date -1d in case
        start_date = datetime.datetime.strptime(reception_date, '%Y-%m-%d') - datetime.timedelta(days=1)
        recalculate_positions(start_date=start_date, fund_id=int(fund_id))
        return start_date
    else:
        conn.close()  
        flash(f'Ignoring duplicate transaction for fund {fund_id} on {reception_date} with quantity {quantity} and type {trans_type}.', 'warning')
        return None


@bp_transactions.route('/transactions/csvimportMonex', methods=['POST'])
def import_transactions_from_csv_monex():   
    try:
        file = request.files.get('csv_file')
        if not file:
            flash('No file uploaded.', 'error')
            return redirect(url_for('bp_transactions.transactions_page'))
        
        # Process the CSV file and import transactions
        import csv
        s = file.stream.read().decode('shift_jis')  # Assuming the CSV is in Shift JIS encoding 
        reader = csv.DictReader(s.splitlines())
        for row in reader:
            fund_name = row.get('銘柄名')
            csv_trans_type = row.get('取引区分')

            if csv_trans_type == '買付（累投）':
                csv_reception_date = str(row.get('受渡日')).replace('/', '-')  # Convert date format if needed to expected "YYYY-MM-DD"
                csv_quantity = int(row.get('数量'))
                csv_amount = int(str(row.get('受渡金額')).replace('-', ''))  # Remove commas from the amount
                csv_price = int(row.get('約定価格'))

                #purchase transaction, insert into DB
                print(f"Found purchase transaction in CSV for fund {fund_name} on {csv_reception_date} with quantity {csv_quantity} and amount {csv_amount}")

                # Get fund ID from name
                # The Monex file uses the full name of the fund and not code, so we need to find the fund ID based on the full name. This is not optimal but we don't have the full name in the DB, only the code, so we need to do this transcoding here. 
                funds = get_all_funds()
                fund_id = None
                for f in funds:
                    if "monex_fullname"in f.codes and f.codes["monex_fullname"] == fund_name:
                        fund_id = f.fund_id
                        break
                if not fund_id:
                    #missing transcoding: aborting
                    flash(f'Fund "{fund_name}" not found in the system. Failed importing this transactions, moving to next.', 'error')
                    continue

                # Save transaction to DB
                xact_save_to_db(fund_id, 'お買付', csv_reception_date, csv_quantity, csv_amount, csv_price)
                print(f"Transaction for fund {fund_name} of amount {csv_amount} imported successfully.")




        flash('Transactions imported successfully from CSV.', 'success')
    except Exception as e:
        flash(f'Error importing transactions from CSV: {e}', 'error')
        print(e)

    return redirect(url_for('bp_transactions.transactions_page')) 