from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Registrar blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.usuarios import bp as usuarios_bp
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')

    from app.productos import bp as productos_bp
    app.register_blueprint(productos_bp, url_prefix='/productos')

    from app.inventario import bp as inventario_bp
    app.register_blueprint(inventario_bp, url_prefix='/inventario')

    from app.ventas import bp as ventas_bp
    app.register_blueprint(ventas_bp, url_prefix='/ventas')

    from app.cortesias import bp as cortesias_bp
    app.register_blueprint(cortesias_bp, url_prefix='/cortesias')

    from app.creditos import bp as creditos_bp
    app.register_blueprint(creditos_bp, url_prefix='/creditos')

    from app.gastos import bp as gastos_bp
    app.register_blueprint(gastos_bp, url_prefix='/gastos')

    from app.reportes import bp as reportes_bp
    app.register_blueprint(reportes_bp, url_prefix='/reportes')

    from app.terceros import bp as terceros_bp
    app.register_blueprint(terceros_bp, url_prefix='/terceros')

    # Manejar errores CSRF sin sacar al usuario
    from flask_wtf.csrf import CSRFError
    from flask import flash, redirect, request, url_for

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('La sesión expiró. Intenta de nuevo.', 'warning')
        return redirect(request.referrer or url_for('main.index'))

    # Sesión permanente
    @app.before_request
    def make_session_permanent():
        from flask import session
        session.permanent = True

    return app
