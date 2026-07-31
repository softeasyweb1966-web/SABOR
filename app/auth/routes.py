from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, CambiarClaveForm
from app.models import Usuario
from app.decorators import rol_requerido


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(username=form.username.data).first()
        if usuario and usuario.check_password(form.password.data):
            if not usuario.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(usuario, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/cambiar-clave', methods=['GET', 'POST'])
@login_required
def cambiar_clave():
    """Cualquier usuario puede cambiar su propia clave."""
    form = CambiarClaveForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.clave_actual.data):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('auth/cambiar_clave.html', form=form)

        current_user.set_password(form.clave_nueva.data)
        db.session.commit()
        flash('Contraseña cambiada exitosamente.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/cambiar_clave.html', form=form)


@bp.route('/restablecer/<int:id>', methods=['POST'])
@login_required
@rol_requerido('Administrador')
def restablecer_clave(id):
    """El administrador restablece la clave de un usuario."""
    usuario = Usuario.query.get_or_404(id)
    nueva_clave = request.form.get('nueva_clave', '').strip()

    if not nueva_clave or len(nueva_clave) < 4:
        flash('La clave debe tener al menos 4 caracteres.', 'danger')
        return redirect(url_for('usuarios.listar'))

    usuario.set_password(nueva_clave)
    db.session.commit()
    flash(f'Clave de {usuario.nombre_completo} restablecida.', 'success')
    return redirect(url_for('usuarios.listar'))


@bp.route('/inhabilitar/<int:id>', methods=['POST'])
@login_required
@rol_requerido('Administrador')
def inhabilitar_usuario(id):
    """El administrador inhabilita/habilita un usuario."""
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes inhabilitarte a ti mismo.', 'danger')
        return redirect(url_for('usuarios.listar'))

    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'habilitado' if usuario.activo else 'inhabilitado'
    flash(f'Usuario {usuario.nombre_completo} {estado}.', 'success')
    return redirect(url_for('usuarios.listar'))
