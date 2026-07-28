from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.auth.forms import LoginForm
from app.models import Usuario


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
