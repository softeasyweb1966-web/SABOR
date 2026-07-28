from flask import Blueprint

bp = Blueprint('productos', __name__, template_folder='templates')

from app.productos import routes  # noqa
