from flask import  render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav
from datetime import datetime

from config import conf

bp_admin = Blueprint('bp_admin', __name__)

@bp_admin.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if request.method == 'POST':
        # Handle form submission
        conf.risk_free_rate = float(request.form.get('riskFreeRate', 0.03))
        
    return render_template('admin.html', conf=conf)