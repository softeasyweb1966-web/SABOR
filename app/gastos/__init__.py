from flask import Blueprint

bp = Blueprint('gastos', __name__, template_folder='templates')

from app.gastos import routes  # noqa
