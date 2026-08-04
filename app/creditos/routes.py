from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.creditos import bp
from app.creditos.forms import CreditoForm, PagoCreditoForm
from app.models import Credito, PagoCredito, Persona, FormaPago
from decimal import Decimal


@bp.route('/')
@login_required
def index():
    estado = request.args.get('estado', 'pendiente')
    if estado == 'todos':
        creditos = Credito.query.order_by(Credito.fecha.desc()).all()
    elif estado == 'pendiente':
        # Mostrar todos los que tienen saldo pendiente (pendiente + abonado)
        creditos = Credito.query.filter(
            Credito.estado.in_(['pendiente', 'abonado'])
        ).order_by(Credito.fecha.desc()).all()
    else:
        creditos = Credito.query.filter_by(estado=estado).order_by(Credito.fecha.desc()).all()

    total_pendiente = sum(c.saldo_pendiente for c in Credito.query.filter(
        Credito.estado.in_(['pendiente', 'abonado'])
    ).all())
    return render_template('creditos/index.html', creditos=creditos, estado=estado, total_pendiente=total_pendiente)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = CreditoForm()
    form.persona_id.choices = [(p.id, p.nombre) for p in Persona.query.filter_by(activa=True).order_by(Persona.nombre).all()]

    if form.validate_on_submit():
        credito = Credito(
            persona_id=form.persona_id.data,
            monto_total=form.monto_total.data,
            saldo_pendiente=form.monto_total.data,
            fecha=form.fecha.data,
            observacion=form.observacion.data,
            estado='pendiente'
        )
        db.session.add(credito)
        db.session.commit()
        flash('Crédito registrado.', 'success')
        return redirect(url_for('creditos.index'))

    return render_template('creditos/credito_form.html', form=form)


@bp.route('/<int:id>/detalle')
@login_required
def detalle(id):
    credito = Credito.query.get_or_404(id)
    form = PagoCreditoForm()
    form.forma_pago_id.choices = [(f.id, f.nombre) for f in FormaPago.query.filter_by(activa=True).all()]
    return render_template('creditos/detalle.html', credito=credito, form=form)


@bp.route('/<int:id>/abonar', methods=['POST'])
@login_required
def abonar(id):
    credito = Credito.query.get_or_404(id)
    form = PagoCreditoForm()
    form.forma_pago_id.choices = [(f.id, f.nombre) for f in FormaPago.query.filter_by(activa=True).all()]

    if form.validate_on_submit():
        monto = form.monto.data

        if monto > credito.saldo_pendiente:
            flash(f'El abono no puede ser mayor al saldo pendiente (${credito.saldo_pendiente:,.0f}).', 'danger')
            return redirect(url_for('creditos.detalle', id=id))

        pago = PagoCredito(
            credito_id=id,
            monto=monto,
            forma_pago_id=form.forma_pago_id.data,
            fecha=form.fecha.data,
            observacion=form.observacion.data
        )
        credito.saldo_pendiente -= monto

        if credito.saldo_pendiente <= 0:
            credito.saldo_pendiente = Decimal('0')
            credito.estado = 'cancelado'
            flash('Crédito cancelado totalmente.', 'success')
        else:
            credito.estado = 'abonado'
            flash(f'Abono de ${monto:,.0f} registrado. Saldo pendiente: ${credito.saldo_pendiente:,.0f}', 'success')

        db.session.add(pago)
        db.session.commit()

    return redirect(url_for('creditos.detalle', id=id))


@bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    credito = Credito.query.get_or_404(id)
    # Eliminar pagos asociados
    PagoCredito.query.filter_by(credito_id=id).delete()
    db.session.delete(credito)
    db.session.commit()
    flash('Crédito eliminado.', 'success')
    return redirect(url_for('creditos.index'))


@bp.route('/estado-cuenta')
@login_required
def estado_cuenta():
    """Estado de cuenta de una persona: todos sus créditos y pagos."""
    persona_id = request.args.get('persona_id', type=int)

    # Lista de personas con créditos pendientes
    personas_con_creditos = db.session.query(Persona).join(Credito).filter(
        Credito.estado.in_(['pendiente', 'abonado'])
    ).distinct().order_by(Persona.nombre).all()

    # Resumen de deuda por persona (para vista "todos")
    resumen_todos = []
    total_general = Decimal('0')
    for p in personas_con_creditos:
        deuda = sum(c.saldo_pendiente for c in p.creditos if c.estado in ['pendiente', 'abonado'])
        if deuda > 0:
            resumen_todos.append({'persona': p, 'deuda': deuda})
            total_general += deuda

    persona = None
    creditos_persona = []
    total_deuda = Decimal('0')
    total_creditos = Decimal('0')
    total_pagado = Decimal('0')

    if persona_id:
        persona = Persona.query.get(persona_id)
        if persona:
            creditos_persona = Credito.query.filter_by(persona_id=persona_id).order_by(Credito.fecha.desc()).all()
            total_deuda = sum(c.saldo_pendiente for c in creditos_persona if c.estado in ['pendiente', 'abonado'])
            total_creditos = sum(c.monto_total for c in creditos_persona)
            total_pagado = total_creditos - total_deuda

    return render_template('creditos/estado_cuenta.html',
                           personas=personas_con_creditos,
                           persona=persona,
                           persona_id=persona_id,
                           creditos_persona=creditos_persona,
                           total_deuda=total_deuda,
                           total_creditos=total_creditos,
                           total_pagado=total_pagado,
                           resumen_todos=resumen_todos,
                           total_general=total_general)
