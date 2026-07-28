from flask import Blueprint

bp = Blueprint('cortesias', __name__, template_folder='templates')

from app.cortesias import routes  # noqa
