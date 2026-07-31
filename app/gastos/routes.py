from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.gastos import bp
from app.gastos.forms import TipoGastoForm, GastoForm
from app.models import TipoGasto, Gasto
from app.decorators import rol_requerido
from datetime import date


@bp.route('/')
@login_required
@rol_requerido('Administrador', 'Compras')
def index():
    mes = request.args.get('mes', date.today().month, type=int)
    anio = request.args.get('anio', date.today().year, type=int)

    gastos = Gasto.query.filter(
        db.extract('month', Gasto.fecha) == mes,
        db.extract('year', Gasto.fecha) == anio
    ).order_by(Gasto.fecha.desc()).all()

    total_mes = sum(g.monto for g in gastos)
    return render_template('gastos/index.html', gastos=gastos, mes=mes, anio=anio, total_mes=total_mes)


@bp.route('/tipos')
@login_required
def tipos():
    tipos = TipoGasto.query.order_by(TipoGasto.nombre).all()
    return render_template('gastos/tipos.html', tipos=tipos)


@bp.route('/tipos/crear', methods=['GET', 'POST'])
@login_required
def crear_tipo():
    form = TipoGastoForm()
    if form.validate_on_submit():
        tipo = TipoGasto(nombre=form.nombre.data, activo=form.activo.data)
        db.session.add(tipo)
        db.session.commit()
        flash('Tipo de gasto creado.', 'success')
        return redirect(url_for('gastos.tipos'))
    return render_template('gastos/tipo_form.html', form=form, titulo='Crear Tipo de Gasto')


@bp.route('/tipos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tipo(id):
    tipo = TipoGasto.query.get_or_404(id)
    form = TipoGastoForm(obj=tipo)
    if form.validate_on_submit():
        tipo.nombre = form.nombre.data
        tipo.activo = form.activo.data
        db.session.commit()
        flash('Tipo de gasto actualizado.', 'success')
        return redirect(url_for('gastos.tipos'))
    return render_template('gastos/tipo_form.html', form=form, titulo='Editar Tipo de Gasto')


@bp.route('/tipos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_tipo(id):
    tipo = TipoGasto.query.get_or_404(id)
    if tipo.gastos:
        flash('No se puede eliminar: tiene gastos asociados.', 'danger')
    else:
        db.session.delete(tipo)
        db.session.commit()
        flash('Tipo de gasto eliminado.', 'success')
    return redirect(url_for('gastos.tipos'))


@bp.route('/registrar', methods=['GET', 'POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def registrar():
    form = GastoForm()
    form.tipo_gasto_id.choices = [(t.id, t.nombre) for t in TipoGasto.query.filter_by(activo=True).order_by(TipoGasto.nombre).all()]

    if form.validate_on_submit():
        gasto = Gasto(
            tipo_gasto_id=form.tipo_gasto_id.data,
            descripcion=form.descripcion.data,
            detalle=form.detalle.data,
            monto=form.monto.data,
            forma_pago=form.forma_pago.data,
            fecha=form.fecha.data,
            usuario_id=current_user.id
        )
        db.session.add(gasto)
        db.session.commit()
        flash('Gasto registrado.', 'success')
        return redirect(url_for('gastos.index'))

    return render_template('gastos/gasto_form.html', form=form)


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    gasto = Gasto.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto eliminado.', 'success')
    return redirect(url_for('gastos.index'))
