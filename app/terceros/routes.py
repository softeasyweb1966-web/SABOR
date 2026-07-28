from flask import render_template, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.terceros import bp
from app.terceros.forms import TerceroForm
from app.models import Persona


@bp.route('/')
@login_required
def listar():
    personas = Persona.query.order_by(Persona.nombre).all()
    return render_template('terceros/listar.html', personas=personas)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = TerceroForm()
    if form.validate_on_submit():
        persona = Persona(
            nombre=form.nombre.data,
            telefono=form.telefono.data,
            tipo=form.tipo.data,
            observacion=form.observacion.data,
            activa=form.activa.data
        )
        db.session.add(persona)
        db.session.commit()
        flash('Tercero creado exitosamente.', 'success')
        return redirect(url_for('terceros.listar'))
    return render_template('terceros/form.html', form=form, titulo='Nuevo Tercero')


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    persona = Persona.query.get_or_404(id)
    form = TerceroForm(obj=persona)
    if form.validate_on_submit():
        persona.nombre = form.nombre.data
        persona.telefono = form.telefono.data
        persona.tipo = form.tipo.data
        persona.observacion = form.observacion.data
        persona.activa = form.activa.data
        db.session.commit()
        flash('Tercero actualizado.', 'success')
        return redirect(url_for('terceros.listar'))
    return render_template('terceros/form.html', form=form, titulo='Editar Tercero')


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    persona = Persona.query.get_or_404(id)
    if persona.cortesias or persona.creditos:
        flash('No se puede eliminar: tiene cortesías o créditos asociados.', 'danger')
    else:
        db.session.delete(persona)
        db.session.commit()
        flash('Tercero eliminado.', 'success')
    return redirect(url_for('terceros.listar'))
