from flask import Blueprint

bp = Blueprint('reportes', __name__, template_folder='templates')

from app.reportes import routes  # noqa
