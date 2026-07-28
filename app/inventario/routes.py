from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.inventario import bp
from app.inventario.forms import InsumoForm, CompraForm, CategoriaCompraForm
from app.models import Insumo, Compra, CategoriaCompra, VentaDiaria, VentaDetalle, ProductoInsumo
from datetime import date, timedelta
from decimal import Decimal


# ============================================================
# VISTA PRINCIPAL: MOVIMIENTOS DEL DÍA
# ============================================================

@bp.route('/')
@login_required
def listar():
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            from datetime import datetime
            fecha_sel = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_sel = None
    else:
        fecha_sel = None

    # Si no se seleccionó fecha, buscar el último día con ventas cerradas
    if not fecha_sel:
        ultimo_dia = VentaDiaria.query.filter(
            VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
        ).order_by(VentaDiaria.fecha.desc()).first()
        if ultimo_dia:
            fecha_sel = ultimo_dia.fecha
        else:
            fecha_sel = date.today()

    # Buscar la venta diaria de esa fecha
    venta_dia = VentaDiaria.query.filter_by(fecha=fecha_sel).first()

    # Buscar movimientos guardados para esa fecha
    from app.models import MovimientoInventario
    movimientos = MovimientoInventario.query.filter_by(fecha=fecha_sel).all()
    movimientos.sort(key=lambda x: x.insumo.nombre)

    # Lista de días disponibles para el selector
    dias_disponibles = VentaDiaria.query.filter(
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha.desc()).limit(15).all()

    return render_template('inventario/listar.html',
                           movimientos=movimientos,
                           fecha_sel=fecha_sel,
                           venta_dia=venta_dia,
                           dias_disponibles=dias_disponibles)


# ============================================================
# INSUMOS CRUD
# ============================================================

@bp.route('/insumos')
@login_required
def insumos():
    insumos = Insumo.query.order_by(Insumo.nombre).all()
    return render_template('inventario/insumos.html', insumos=insumos)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_insumo():
    form = InsumoForm()
    if form.validate_on_submit():
        insumo = Insumo(
            nombre=form.nombre.data,
            unidad_medida=form.unidad_medida.data,
            stock_minimo=form.stock_minimo.data or 0,
            activo=form.activo.data
        )
        db.session.add(insumo)
        db.session.commit()
        flash('Insumo creado exitosamente.', 'success')
        return redirect(url_for('inventario.insumos'))
    return render_template('inventario/insumo_form.html', form=form, titulo='Crear Insumo')


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_insumo(id):
    insumo = Insumo.query.get_or_404(id)
    form = InsumoForm(obj=insumo)
    if form.validate_on_submit():
        insumo.nombre = form.nombre.data
        insumo.unidad_medida = form.unidad_medida.data
        insumo.stock_minimo = form.stock_minimo.data or 0
        insumo.activo = form.activo.data
        db.session.commit()
        flash('Insumo actualizado.', 'success')
        return redirect(url_for('inventario.insumos'))
    return render_template('inventario/insumo_form.html', form=form, titulo='Editar Insumo')


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_insumo(id):
    insumo = Insumo.query.get_or_404(id)
    if insumo.productos_asociados:
        flash('No se puede eliminar: está asociado a productos.', 'danger')
    else:
        db.session.delete(insumo)
        db.session.commit()
        flash('Insumo eliminado.', 'success')
    return redirect(url_for('inventario.insumos'))


# ============================================================
# CATEGORÍAS DE COMPRA
# ============================================================

@bp.route('/categorias-compra')
@login_required
def categorias_compra():
    categorias = CategoriaCompra.query.order_by(CategoriaCompra.nombre).all()
    return render_template('inventario/categorias_compra.html', categorias=categorias)


@bp.route('/categorias-compra/crear', methods=['GET', 'POST'])
@login_required
def crear_categoria_compra():
    form = CategoriaCompraForm()
    if form.validate_on_submit():
        cat = CategoriaCompra(nombre=form.nombre.data, activa=form.activa.data)
        db.session.add(cat)
        db.session.commit()
        flash('Categoría de compra creada.', 'success')
        return redirect(url_for('inventario.categorias_compra'))
    return render_template('inventario/categoria_compra_form.html', form=form, titulo='Nueva Categoría de Compra')


@bp.route('/categorias-compra/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria_compra(id):
    cat = CategoriaCompra.query.get_or_404(id)
    form = CategoriaCompraForm(obj=cat)
    if form.validate_on_submit():
        cat.nombre = form.nombre.data
        cat.activa = form.activa.data
        db.session.commit()
        flash('Categoría actualizada.', 'success')
        return redirect(url_for('inventario.categorias_compra'))
    return render_template('inventario/categoria_compra_form.html', form=form, titulo='Editar Categoría de Compra')


@bp.route('/categorias-compra/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria_compra(id):
    cat = CategoriaCompra.query.get_or_404(id)
    if cat.compras:
        flash('No se puede eliminar: tiene compras asociadas.', 'danger')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash('Categoría eliminada.', 'success')
    return redirect(url_for('inventario.categorias_compra'))


# ============================================================
# COMPRAS
# ============================================================

@bp.route('/compras')
@login_required
def compras():
    cat_id = request.args.get('categoria', type=int)
    query = Compra.query
    if cat_id:
        query = query.filter_by(categoria_compra_id=cat_id)
    compras = query.order_by(Compra.fecha.desc()).limit(100).all()
    categorias = CategoriaCompra.query.filter_by(activa=True).order_by(CategoriaCompra.nombre).all()
    return render_template('inventario/compras.html', compras=compras, categorias=categorias, cat_sel=cat_id)


@bp.route('/compras/registrar', methods=['GET', 'POST'])
@login_required
def registrar_compra():
    form = CompraForm()
    form.categoria_compra_id.choices = [(c.id, c.nombre) for c in CategoriaCompra.query.filter_by(activa=True).order_by(CategoriaCompra.nombre).all()]
    form.insumo_id.choices = [(i.id, f"{i.nombre} ({i.unidad_medida})") for i in Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()]

    if form.validate_on_submit():
        compra = Compra(
            categoria_compra_id=form.categoria_compra_id.data,
            insumo_id=form.insumo_id.data,
            cantidad=form.cantidad.data,
            costo_total=form.costo_total.data,
            proveedor=form.proveedor.data,
            fecha=form.fecha.data,
            observacion=form.observacion.data,
            usuario_id=current_user.id
        )
        # Actualizar stock del insumo
        insumo = Insumo.query.get(form.insumo_id.data)
        insumo.stock_actual += form.cantidad.data

        db.session.add(compra)
        db.session.commit()
        flash(f'Compra registrada. Stock de "{insumo.nombre}" actualizado a {insumo.stock_actual} {insumo.unidad_medida}.', 'success')
        return redirect(url_for('inventario.compras'))

    return render_template('inventario/compra_form.html', form=form)


@bp.route('/compras/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_compra(id):
    compra = Compra.query.get_or_404(id)
    # Revertir stock
    insumo = Insumo.query.get(compra.insumo_id)
    insumo.stock_actual -= compra.cantidad
    db.session.delete(compra)
    db.session.commit()
    flash('Compra eliminada y stock revertido.', 'success')
    return redirect(url_for('inventario.compras'))
