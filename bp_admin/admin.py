from flask import  render_template, request, Blueprint
from shared import get_all_funds, import_latest_nav, import_history_nav
from datetime import datetime

bp_admin = Blueprint('bp_admin', __name__)

@bp_admin.route('/admin')
def admin_page():
    return render_template('admin.html')