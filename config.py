import os
from dotenv import load_dotenv

load_dotenv()


def _build_database_uri():
    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://postgres:PreventPg2026Local1@127.0.0.1:5432/sabor_db'
    )

    # Algunos hostings exponen la URL con el esquema legacy "postgres://",
    # pero SQLAlchemy espera "postgresql://".
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    return database_url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Sin expiracion de token CSRF
    PERMANENT_SESSION_LIFETIME = 86400  # Sesion dura 24 horas
    REMEMBER_COOKIE_DURATION = 604800  # Cookie "recordarme" dura 7 dias
