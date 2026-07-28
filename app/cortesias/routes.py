from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.cortesias import bp
from app.cortesias.forms import PersonaForm, CortesiaForm
from app.models import Persona, Cortesia, Producto, Categoria
from datetime import date


# ============================================================
# PERSONAS
# ============================================================

@bp.route('/')
@login_required
def index():
    personas = Persona.query.order_by(Persona.nombre).all()
    return render_template('cortesias/index.html', personas=personas)


@bp.route('/personas/crear', methods=['GET', 'POST'])
@login_required
def crear_persona():
    form = PersonaForm()
    if form.validate_on_submit():
        persona = Persona(
            nombre=form.nombre.data,
            telefono=form.telefono.data,
            observacion=form.observacion.data,
            activa=form.activa.data
        )
        db.session.add(persona)
        db.session.commit()
        flash('Persona registrada exitosamente.', 'success')
        return redirect(url_for('cortesias.index'))
    return render_template('cortesias/persona_form.html', form=form, titulo='Registrar Persona')


@bp.route('/personas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_persona(id):
    persona = Persona.query.get_or_404(id)
    form = PersonaForm(obj=persona)
    if form.validate_on_submit():
        persona.nombre = form.nombre.data
        persona.telefono = form.telefono.data
        persona.observacion = form.observacion.data
        persona.activa = form.activa.data
        db.session.commit()
        flash('Persona actualizada.', 'success')
        return redirect(url_for('cortesias.index'))
    return render_template('cortesias/persona_form.html', form=form, titulo='Editar Persona')


@bp.route('/personas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_persona(id):
    persona = Persona.query.get_or_404(id)
    if persona.cortesias:
        flash('No se puede eliminar: tiene cortesías registradas.', 'danger')
    else:
        db.session.delete(persona)
        db.session.commit()
        flash('Persona eliminada.', 'success')
    return redirect(url_for('cortesias.index'))


# ============================================================
# CORTESÍAS
# ============================================================

@bp.route('/registro')
@login_required
def registro():
    mes = request.args.get('mes', date.today().month, type=int)
    anio = request.args.get('anio', date.today().year, type=int)

    # Cortesías registradas en tabla Cortesia (módulo independiente)
    cortesias_tabla = Cortesia.query.filter(
        db.extract('month', Cortesia.fecha) == mes,
        db.extract('year', Cortesia.fecha) == anio
    ).order_by(Cortesia.fecha.desc()).all()

    # Cortesías registradas desde ventas del día (VentaDetalle con es_cortesia=True)
    from app.models import VentaDetalle, VentaDiaria
    ventas_cortesias = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        VentaDetalle.es_cortesia == True,
        db.extract('month', VentaDiaria.fecha) == mes,
        db.extract('year', VentaDiaria.fecha) == anio
    ).order_by(VentaDiaria.fecha.desc()).all()

    return render_template('cortesias/registro.html',
                           cortesias=cortesias_tabla,
                           ventas_cortesias=ventas_cortesias,
                           mes=mes, anio=anio)


@bp.route('/registrar', methods=['GET', 'POST'])
@login_required
def registrar():
    form = CortesiaForm()
    form.persona_id.choices = [(p.id, p.nombre) for p in Persona.query.filter_by(activa=True).order_by(Persona.nombre).all()]

    # Solo productos de la categoría "Almuerzos" para cortesías
    cat_almuerzos = Categoria.query.filter_by(nombre='Almuerzos').first()
    if cat_almuerzos:
        productos = Producto.query.filter_by(categoria_id=cat_almuerzos.id, activo=True).order_by(Producto.nombre).all()
    else:
        productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    form.producto_id.choices = [(p.id, f"{p.nombre} (${p.precio:,.0f})") for p in productos]
    form.persona_id.choices = [(p.id, p.nombre) for p in Persona.query.filter(
        Persona.activa == True,
        Persona.tipo.in_(['cortesia', 'ambos'])
    ).order_by(Persona.nombre).all()]

    if form.validate_on_submit():
        cortesia = Cortesia(
            persona_id=form.persona_id.data,
            producto_id=form.producto_id.data,
            cantidad=form.cantidad.data,
            fecha=form.fecha.data,
            observacion=form.observacion.data
        )
        db.session.add(cortesia)
        db.session.commit()
        flash('Cortesía registrada.', 'success')
        return redirect(url_for('cortesias.registro'))

    return render_template('cortesias/cortesia_form.html', form=form)


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_cortesia(id):
    cortesia = Cortesia.query.get_or_404(id)
    db.session.delete(cortesia)
    db.session.commit()
    flash('Cortesía eliminada.', 'success')
    return redirect(url_for('cortesias.registro'))
