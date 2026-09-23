from flask import render_template, request, Blueprint, redirect, url_for, flash
from shared import get_holdings, get_latest_positions, recalculate_positions, get_all_funds, csv_import_monex_holdings
from config import conf

bp_imports = Blueprint('bp_imports', __name__)

@bp_imports.route('/imports', methods=['GET', 'POST'])
def imports_page():
    
    return render_template('imports.html', conf=conf)


@bp_imports.route('/imports/csvimportMonexHoldingsCompare', methods=['POST'])
def csvimport_monex_holdings_compare():
    # Handle the CSV COMPARISON for Monex holdings here (no update, just comparison)
    if 'csv_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('bp_imports.imports_page'))
    file = request.files['csv_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('bp_imports.imports_page'))
    if file:
        # Process the CSV file here

        holdings_compare = []
        holdings_fmc = get_latest_positions()  # Example: Replace with actual logic to compare holdings
        holdings_monex = csv_import_monex_holdings(file.stream.read())

        for holding_fmc in holdings_fmc:
            print(holding_fmc)
            monex_holding = next((h['holding'] for h in holdings_monex if h['fund_id'] == holding_fmc['fund_id']), 0)
            holdings_compare.append({
                'fund': holding_fmc['name'],
                'fund_id': holding_fmc['fund_id'],
                'holding': holding_fmc['latest_unit'],
                'monex_holding': monex_holding,
                'difference': holding_fmc['latest_unit'] - monex_holding
            })

        #sort
        holdings_compare.sort(key=lambda x: abs(x['difference']), reverse=True)

        #remove empties where we agree (both holdings are zero)
        holdings_compare = [h for h in holdings_compare if h['holding'] != 0 or h['monex_holding'] != 0]

        flash('File successfully uploaded', 'success')
        return render_template('imports.html', conf=conf, holdings=holdings_compare)




@bp_imports.route('/imports/csvimportMonexHoldingsUpdate', methods=['POST'])
def csvimport_monex_holdings_update():
    # Handle the CSV import for Monex holdings here
    if 'csv_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('bp_imports.imports_page'))
    file = request.files['csv_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('bp_imports.imports_page'))
    if file:
        # Process the CSV file here

        holdings_compare = []
        holdings_fmc = get_latest_positions()  # Example: Replace with actual logic to compare holdings
        holdings_monex = csv_import_monex_holdings(file.stream.read())

        for holding_fmc in holdings_fmc:
            print(holding_fmc)
            monex_holding = next((h['holding'] for h in holdings_monex if h['fund_id'] == holding_fmc['fund_id']), 0)
            holdings_compare.append({
                'fund': holding_fmc['name'],
                'fund_id': holding_fmc['fund_id'],
                'holding': holding_fmc['latest_unit'],
                'monex_holding': monex_holding,
                'difference': holding_fmc['latest_unit'] - monex_holding
            })

        #remove empties where we agree (both holdings are zero)
        holdings_compare = [h for h in holdings_compare if h['holding'] != 0 or h['monex_holding'] != 0]

        #remove holdings where the difference is zero
        holdings_compare = [h for h in holdings_compare if h['difference'] != 0]

        flash(f'File successfully uploaded: {len(holdings_compare)} differences found', 'success')

        #TODO genreate update orders for FMC based on the differences found of type '再投資買付'

        flash('STOPPED HERE!', 'error')

        return render_template('imports.html', conf=conf, holdings=holdings_compare)