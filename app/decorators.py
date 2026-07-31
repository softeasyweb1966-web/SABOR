from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def rol_requerido(*roles_permitidos):
    """Decorador para restringir acceso por rol.
    Uso: @rol_requerido('Administrador', 'Caja')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.rol.nombre not in roles_permitidos:
                flash('No tienes permisos para acceder a esta opción.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
