from flask import  flash, render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav
from datetime import datetime
from fund import Fund

from config import conf

bp_admin = Blueprint('bp_admin', __name__)

@bp_admin.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if request.method == 'POST':
        print(f"DBG Form data received : {request.form}")

        if request.form.get("submit_button", "?") == "Save Settings":
            # Handle form submission FOR SAVE SETTINGS
            conf.risk_free_rate = float(request.form.get('riskFreeRate', 0.03))
            flash('Settings saved successfully.', 'success')

        elif request.form.get("submit_button", "?") == "Delete fund":
            # Handle form submission FOR DELETE FUND
            fund_id = request.form.get("deleteFund")
            if fund_id:
                # Handle fund deletion
                print(f"Deleting fund with ID: {fund_id}")

                res = Fund.delete_fund(fund_id)

                if res:
                    flash(f'Fund with ID {fund_id} deleted successfully.', 'success')
                else:
                    flash(f'Failed to delete fund with ID {fund_id}.', 'error')
            else:
                flash('No fund ID provided for deletion.', 'error')
        elif request.form.get("submit_button", "?") == "Backup database":
            # Handle form submission FOR BACKUP DATABASE
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                import shutil
                import os
                backup_fullpath = os.path.join(os.path.dirname(conf['DB_PATH']), backup_filename)
                shutil.copyfile(conf['DB_PATH'], backup_fullpath)
                flash(f'Database backed up successfully as {backup_filename}.', 'success')
            except Exception as e:
                flash(f'Failed to back up database: {e}', 'error')
        else:
            flash('Unknown action.', 'error')

    funds = get_all_funds(forced_reload=True)  # Refresh fund list
    return render_template('admin.html', conf=conf, funds=funds)