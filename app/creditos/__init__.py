from flask import Blueprint

bp = Blueprint('creditos', __name__, template_folder='templates')

from app.creditos import routes  # noqa
