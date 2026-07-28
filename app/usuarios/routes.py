from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.usuarios import bp
from app.usuarios.forms import UsuarioForm, UsuarioEditForm
from app.models import Usuario, Rol


@bp.route('/')
@login_required
def listar():
    usuarios = Usuario.query.order_by(Usuario.nombre_completo).all()
    return render_template('usuarios/listar.html', usuarios=usuarios)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = UsuarioForm()
    form.rol_id.choices = [(r.id, r.nombre) for r in Rol.query.order_by(Rol.nombre).all()]

    if form.validate_on_submit():
        usuario = Usuario(
            username=form.username.data,
            email=form.email.data,
            nombre_completo=form.nombre_completo.data,
            rol_id=form.rol_id.data,
            activo=form.activo.data
        )
        usuario.set_password(form.password.data)
        db.session.add(usuario)
        db.session.commit()
        flash('Usuario creado exitosamente.', 'success')
        return redirect(url_for('usuarios.listar'))

    return render_template('usuarios/crear.html', form=form)


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    usuario = Usuario.query.get_or_404(id)
    form = UsuarioEditForm(obj=usuario)
    form.rol_id.choices = [(r.id, r.nombre) for r in Rol.query.order_by(Rol.nombre).all()]

    if form.validate_on_submit():
        # Validar unicidad manualmente
        existing = Usuario.query.filter_by(username=form.username.data).first()
        if existing and existing.id != id:
            flash('Este nombre de usuario ya existe.', 'danger')
            return render_template('usuarios/editar.html', form=form, usuario=usuario)

        existing_email = Usuario.query.filter_by(email=form.email.data).first()
        if existing_email and existing_email.id != id:
            flash('Este email ya está registrado.', 'danger')
            return render_template('usuarios/editar.html', form=form, usuario=usuario)

        usuario.username = form.username.data
        usuario.email = form.email.data
        usuario.nombre_completo = form.nombre_completo.data
        usuario.rol_id = form.rol_id.data
        usuario.activo = form.activo.data

        if form.password.data:
            usuario.set_password(form.password.data)

        db.session.commit()
        flash('Usuario actualizado exitosamente.', 'success')
        return redirect(url_for('usuarios.listar'))

    return render_template('usuarios/editar.html', form=form, usuario=usuario)


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'danger')
        return redirect(url_for('usuarios.listar'))

    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('usuarios.listar'))
