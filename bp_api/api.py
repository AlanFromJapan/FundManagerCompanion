from flask import Blueprint
from shared import get_all_funds, import_history_nav, recalculate_positions

bp_api = Blueprint('bp_api', __name__)

@bp_api.route('/api/daily_update', methods=['GET'])
def daily_update():
    # Call the function to import the whole NAV data
    try:
        funds_list = get_all_funds()  # Refresh fund list cache
        for fund in funds_list:
            import_history_nav(fund)
        
        recalculate_positions()

        return "Daily update completed successfully.", 200

    except Exception as e:
        return "Error occurred during daily update.", 500
