from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.productos import bp
from app.productos.forms import CategoriaForm, ProductoForm, RecetaForm
from app.models import Categoria, Producto, Receta
from app.decorators import rol_requerido


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
            visible_ventas=form.visible_ventas.data,
            visible_compras=form.visible_compras.data,
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
        categoria.visible_ventas = form.visible_ventas.data
        categoria.visible_compras = form.visible_compras.data
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
    query = Producto.query.filter_by(activo=True)
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    productos = query.order_by(Producto.nombre).all()
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
    return render_template('productos/listar.html', productos=productos, categorias=categorias, categoria_sel=categoria_id)


@bp.route('/crear', methods=['GET', 'POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def crear():
    form = ProductoForm()
    form.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()]

    if form.validate_on_submit():
        producto = Producto(
            nombre=form.nombre.data,
            categoria_id=form.categoria_id.data,
            tipo=form.tipo.data,
            precio=form.precio.data or 0,
            se_vende=form.se_vende.data,
            maneja_inventario=form.maneja_inventario.data,
            unidad_medida=form.unidad_medida.data if form.maneja_inventario.data else 'unidades',
            stock_minimo=form.stock_minimo.data or 0,
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

    if form.validate_on_submit():
        producto.nombre = form.nombre.data
        producto.categoria_id = form.categoria_id.data
        producto.tipo = form.tipo.data
        producto.precio = form.precio.data or 0
        producto.se_vende = form.se_vende.data
        producto.maneja_inventario = form.maneja_inventario.data
        producto.unidad_medida = form.unidad_medida.data if form.maneja_inventario.data else 'unidades'
        producto.stock_minimo = form.stock_minimo.data or 0
        producto.activo = form.activo.data
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('productos.listar'))
    return render_template('productos/producto_form.html', form=form, titulo='Editar Producto')


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    # Eliminar recetas donde este producto es ingrediente
    Receta.query.filter_by(insumo_id=id).delete()
    # Eliminar recetas propias del producto
    Receta.query.filter_by(producto_id=id).delete()
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('productos.listar'))


# ============================================================
# RECETAS (qué se descuenta al vender)
# ============================================================

@bp.route('/<int:id>/receta')
@login_required
def receta(id):
    producto = Producto.query.get_or_404(id)
    form = RecetaForm()
    # Solo productos que manejan inventario pueden ser insumos de una receta
    form.insumo_id.choices = [(p.id, f"{p.nombre} ({p.unidad_medida})") for p in
                              Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
                              if p.id != id]
    return render_template('productos/receta.html', producto=producto, form=form)


@bp.route('/<int:id>/receta/agregar', methods=['POST'])
@login_required
def agregar_receta(id):
    producto = Producto.query.get_or_404(id)
    form = RecetaForm()
    form.insumo_id.choices = [(p.id, p.nombre) for p in
                              Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
                              if p.id != id]

    if form.validate_on_submit():
        existente = Receta.query.filter_by(producto_id=id, insumo_id=form.insumo_id.data).first()
        if existente:
            flash('Este producto ya está en la receta.', 'warning')
        else:
            r = Receta(producto_id=id, insumo_id=form.insumo_id.data, cantidad=form.cantidad.data)
            db.session.add(r)
            db.session.commit()
            flash('Ingrediente agregado a la receta.', 'success')
    return redirect(url_for('productos.receta', id=id))


@bp.route('/<int:producto_id>/receta/eliminar/<int:receta_id>', methods=['POST'])
@login_required
def eliminar_receta(producto_id, receta_id):
    r = Receta.query.get_or_404(receta_id)
    db.session.delete(r)
    db.session.commit()
    flash('Ingrediente removido de la receta.', 'success')
    return redirect(url_for('productos.receta', id=producto_id))
