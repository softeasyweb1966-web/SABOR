from flask import Blueprint

bp = Blueprint('ventas', __name__, template_folder='templates')

from app.ventas import routes  # noqa
