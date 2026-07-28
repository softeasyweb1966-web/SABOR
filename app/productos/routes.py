from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.productos import bp
from app.productos.forms import CategoriaForm, ProductoForm, ProductoInsumoForm
from app.models import Categoria, Producto, Insumo, ProductoInsumo


# ============================================================
# CATEGORÍAS
# ============================================================

@bp.route('/categorias')
@login_required
def categorias():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    return render_template('productos/categorias.html', categorias=categorias)


@bp.route('/categorias/crear', methods=['GET', 'POST'])
@login_required
def crear_categoria():
    form = CategoriaForm()
    if form.validate_on_submit():
        categoria = Categoria(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            activa=form.activa.data
        )
        db.session.add(categoria)
        db.session.commit()
        flash('Categoría creada exitosamente.', 'success')
        return redirect(url_for('productos.categorias'))
    return render_template('productos/categoria_form.html', form=form, titulo='Crear Categoría')


@bp.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    form = CategoriaForm(obj=categoria)
    if form.validate_on_submit():
        categoria.nombre = form.nombre.data
        categoria.descripcion = form.descripcion.data
        categoria.activa = form.activa.data
        db.session.commit()
        flash('Categoría actualizada.', 'success')
        return redirect(url_for('productos.categorias'))
    return render_template('productos/categoria_form.html', form=form, titulo='Editar Categoría')


@bp.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    if categoria.productos:
        flash('No se puede eliminar: tiene productos asociados.', 'danger')
    else:
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoría eliminada.', 'success')
    return redirect(url_for('productos.categorias'))


# ============================================================
# PRODUCTOS
# ============================================================

@bp.route('/')
@login_required
def listar():
    categoria_id = request.args.get('categoria', type=int)
    query = Producto.query
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    productos = query.order_by(Producto.nombre).all()
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
    return render_template('productos/listar.html', productos=productos, categorias=categorias, categoria_sel=categoria_id)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = ProductoForm()
    form.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()]
    form.insumo_directo_id.choices = [(0, '-- Ninguno --')] + [(i.id, f"{i.nombre} ({i.unidad_medida})") for i in Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()]

    if form.validate_on_submit():
        insumo_id = form.insumo_directo_id.data if form.controla_inventario_directo.data and form.insumo_directo_id.data != 0 else None
        producto = Producto(
            nombre=form.nombre.data,
            precio=form.precio.data,
            categoria_id=form.categoria_id.data,
            controla_inventario_directo=form.controla_inventario_directo.data,
            insumo_directo_id=insumo_id,
            activo=form.activo.data
        )
        db.session.add(producto)
        db.session.commit()
        flash('Producto creado exitosamente.', 'success')
        return redirect(url_for('productos.listar'))
    return render_template('productos/producto_form.html', form=form, titulo='Crear Producto')


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    producto = Producto.query.get_or_404(id)
    form = ProductoForm(obj=producto)
    form.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()]
    form.insumo_directo_id.choices = [(0, '-- Ninguno --')] + [(i.id, f"{i.nombre} ({i.unidad_medida})") for i in Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()]

    if form.validate_on_submit():
        insumo_id = form.insumo_directo_id.data if form.controla_inventario_directo.data and form.insumo_directo_id.data != 0 else None
        producto.nombre = form.nombre.data
        producto.precio = form.precio.data
        producto.categoria_id = form.categoria_id.data
        producto.controla_inventario_directo = form.controla_inventario_directo.data
        producto.insumo_directo_id = insumo_id
        producto.activo = form.activo.data
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('productos.listar'))
    return render_template('productos/producto_form.html', form=form, titulo='Editar Producto')


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('productos.listar'))


# ============================================================
# DESCUENTOS DE INVENTARIO POR PRODUCTO
# ============================================================

@bp.route('/<int:id>/insumos')
@login_required
def insumos_producto(id):
    producto = Producto.query.get_or_404(id)
    form = ProductoInsumoForm()
    form.insumo_id.choices = [(i.id, f"{i.nombre} ({i.unidad_medida})") for i in Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()]
    return render_template('productos/insumos_producto.html', producto=producto, form=form)


@bp.route('/<int:id>/insumos/agregar', methods=['POST'])
@login_required
def agregar_insumo(id):
    producto = Producto.query.get_or_404(id)
    form = ProductoInsumoForm()
    form.insumo_id.choices = [(i.id, f"{i.nombre} ({i.unidad_medida})") for i in Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()]

    if form.validate_on_submit():
        # Verificar que no exista ya
        existente = ProductoInsumo.query.filter_by(producto_id=id, insumo_id=form.insumo_id.data).first()
        if existente:
            flash('Este insumo ya está asignado al producto.', 'warning')
        else:
            pi = ProductoInsumo(
                producto_id=id,
                insumo_id=form.insumo_id.data,
                cantidad=form.cantidad.data
            )
            db.session.add(pi)
            db.session.commit()
            flash('Insumo asignado al producto.', 'success')
    return redirect(url_for('productos.insumos_producto', id=id))


@bp.route('/<int:producto_id>/insumos/eliminar/<int:pi_id>', methods=['POST'])
@login_required
def eliminar_insumo(producto_id, pi_id):
    pi = ProductoInsumo.query.get_or_404(pi_id)
    db.session.delete(pi)
    db.session.commit()
    flash('Insumo removido del producto.', 'success')
    return redirect(url_for('productos.insumos_producto', id=producto_id))
