from flask import Blueprint

bp = Blueprint('inventario', __name__, template_folder='templates')

from app.inventario import routes  # noqa
