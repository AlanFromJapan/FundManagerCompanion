from flask import render_template, request, Blueprint, redirect, url_for, flash
from shared import get_holdings
import sqlite3
from config import conf
import datetime

bp_holdings = Blueprint('bp_holdings', __name__)


@bp_holdings.route('/holdings', methods=['GET', 'POST'])
def holdings_page():
    pos = get_holdings()
    return render_template('holdings.html', pos=pos)

@bp_holdings.route('/holdings/rerun_position', methods=['POST'])
def rerun_position():

    start_date = request.form.get('start_date') if request.form.get('enable_start_date') else None

    try:
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        exec_date = start_date
        if not start_date:
            cur.execute("SELECT AtDate, * FROM POSITION ORDER BY AtDate DESC LIMIT 1")
            row = cur.fetchone()
            exec_date = row[0]
        
        #make it a datetime object
        exec_date = datetime.datetime.strptime(exec_date, '%Y-%m-%d')
        
        print("Minimal execution date:", exec_date.strftime('%Y-%m-%d'))
        previous_exec_date = exec_date - datetime.timedelta(days=1)
        print("Previous execution date:", previous_exec_date.strftime('%Y-%m-%d'))

        cnt = 0
        #get all the NEW transactions
        cur.execute("SELECT * FROM XACT WHERE ExecutionDate > ? ORDER BY ExecutionDate ASC", (exec_date.strftime('%Y-%m-%d'),))
        xacts = cur.fetchall()


        d = exec_date
        #for every date until yesterday
        while d <= datetime.datetime.today() - datetime.timedelta(days=1):
            # copy the previous day's positions
            cur.execute(
                '''INSERT OR REPLACE INTO "POSITION" (FundID, AtDate, Unit, Amount) 
                SELECT FundID, ?, Unit, Amount FROM POSITION WHERE AtDate = ?''',
                (d.strftime('%Y-%m-%d'), (d - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
            )

            #print(f"▶Processing positions for date: {d.strftime('%Y-%m-%d')} len(xacts)={len(xacts)}")

            # Process transactions for the current date (d = execution date)
            while len(xacts) > 0 and xacts[0][2] == d.strftime('%Y-%m-%d'):
                print("Processing transactions for date:", d.strftime('%Y-%m-%d'))
                row = xacts.pop(0)

                # Process the transaction
                fund_id = row[4]
                exec_date = row[2]
                unit = row[5]
                xact_type = row[3]
                amount = row[6] * unit  # XactPrice is the total price for the units

                if xact_type == 'お買付':
                    #buy
                    pass
                elif xact_type == '再投資買付':
                    #reinvestment buy
                    pass
                elif xact_type == '解約':
                    #sell (redemption)
                    unit = -unit
                    amount = -amount
                else:
                    #skip other types (e.g. dividends, etc.)
                    continue

                print(f"Processing transaction: {xact_type} {unit} units at {amount} each for fund {fund_id} on {exec_date} ")

                #is it the FIRST transaction for this fund?
                if not cur.execute("SELECT * FROM POSITION WHERE FundID = ? LIMIT 1", (fund_id,)).fetchone():
                    #insert a new position record with 0 initial values
                    cur.execute('INSERT INTO POSITION (FundID, AtDate, Unit, Amount) VALUES (?, ?, 0, 0)', (fund_id, d.strftime('%Y-%m-%d')))

                # Update the position
                cur.execute(
                    #TODO FIX don't sum amount, recalculate it with NAV of the date once I have it (future update)
                    'UPDATE POSITION SET Unit = Unit + ?, Amount = Amount + ? WHERE FundID = ? AND AtDate = ?',
                    (unit, amount, fund_id, d.strftime('%Y-%m-%d'))
                )




            #next day
            d = d + datetime.timedelta(days=1)
            cnt += 1


        conn.commit()
        conn.close()
        flash(f'Position recalculation completed. {cnt} days processed.', 'success')
    except Exception as e:
        print("Error recalculating positions:", e)
        flash(f'Error recalculating positions: {e}', 'error')
    return redirect(url_for('bp_holdings.holdings_page'))