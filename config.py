import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:PreventPg2026Local1@127.0.0.1:5432/sabor_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Sin expiración de token CSRF
    PERMANENT_SESSION_LIFETIME = 86400  # Sesión dura 24 horas
    REMEMBER_COOKIE_DURATION = 604800  # Cookie "recordarme" dura 7 días
