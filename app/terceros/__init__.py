from flask import Blueprint

bp = Blueprint('terceros', __name__, template_folder='templates')

from app.terceros import routes  # noqa
