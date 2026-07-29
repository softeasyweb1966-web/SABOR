from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.inventario import bp
from app.inventario.forms import CompraForm
from app.models import Producto, Compra, Categoria


# ============================================================
# INVENTARIO: Lista de productos con stock
# ============================================================

@bp.route('/')
@login_required
def listar():
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
    return render_template('inventario/listar.html', productos=productos)


# ============================================================
# COMPRAS
# ============================================================

@bp.route('/compras')
@login_required
def compras():
    cat_id = request.args.get('categoria', type=int)
    query = Compra.query
    if cat_id:
        query = query.filter_by(categoria_id=cat_id)
    compras_list = query.order_by(Compra.fecha.desc()).limit(100).all()
    categorias = Categoria.query.filter_by(activa=True, visible_compras=True).order_by(Categoria.nombre).all()
    return render_template('inventario/compras.html', compras=compras_list, categorias=categorias, cat_sel=cat_id)


@bp.route('/compras/registrar', methods=['GET', 'POST'])
@login_required
def registrar_compra():
    form = CompraForm()
    form.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.filter_by(activa=True, visible_compras=True).order_by(Categoria.nombre).all()]
    # Todos los productos tipo 'producto' (no servicios) se pueden comprar
    productos_comprables = Producto.query.filter(
        Producto.activo == True,
        Producto.tipo == 'producto'
    ).order_by(Producto.nombre).all()
    form.producto_id.choices = [(p.id, f"{p.nombre} ({p.unidad_medida})") for p in productos_comprables]

    if form.validate_on_submit():
        producto = Producto.query.get(form.producto_id.data)
        compra = Compra(
            producto_id=form.producto_id.data,
            categoria_id=form.categoria_id.data,
            cantidad=form.cantidad.data,
            costo_total=form.costo_total.data,
            proveedor=form.proveedor.data,
            fecha=form.fecha.data,
            observacion=form.observacion.data,
            usuario_id=current_user.id
        )
        # Si maneja inventario, actualizar stock
        if producto.maneja_inventario:
            producto.stock_actual += form.cantidad.data

        db.session.add(compra)
        db.session.commit()

        msg = f'Compra registrada: {producto.nombre} x{form.cantidad.data}'
        if producto.maneja_inventario:
            msg += f' (Stock: {producto.stock_actual} {producto.unidad_medida})'
        flash(msg, 'success')
        return redirect(url_for('inventario.registrar_compra'))

    return render_template('inventario/compra_form.html', form=form)


@bp.route('/compras/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_compra(id):
    compra = Compra.query.get_or_404(id)
    producto = compra.producto
    if producto and producto.maneja_inventario:
        producto.stock_actual -= compra.cantidad
    db.session.delete(compra)
    db.session.commit()
    flash('Compra eliminada y stock revertido.', 'success')
    return redirect(url_for('inventario.compras'))


# ============================================================
# API: Productos por categoría (para filtrar en compras)
# ============================================================

@bp.route('/api/productos-por-categoria/<int:categoria_id>')
@login_required
def productos_por_categoria(categoria_id):
    """Devuelve productos de una categoría que se pueden comprar."""
    # Se pueden comprar: tipo producto + (maneja inventario O no se vende solo)
    # Excluir: los que se venden pero NO manejan inventario (son preparados como almuerzos)
    productos = Producto.query.filter(
        Producto.activo == True,
        Producto.tipo == 'producto',
        Producto.categoria_id == categoria_id,
        db.or_(Producto.maneja_inventario == True, Producto.se_vende == False)
    ).order_by(Producto.nombre).all()
    return jsonify([{'id': p.id, 'nombre': f"{p.nombre} ({p.unidad_medida})"} for p in productos])
