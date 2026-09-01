from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.inventario import bp
from app.inventario.forms import CompraItemForm, ComprobanteForm
from app.models import (Producto, Compra, Categoria, ComprobanteCompra, CajaMenor,
                        MovimientoCajaMenor, AjusteInventario, VentaDiaria, VentaDetalle)
from app.decorators import rol_requerido
from decimal import Decimal
from datetime import date


# ============================================================
# INVENTARIO: Lista de productos con stock
# ============================================================

@bp.route('/')
@login_required
@rol_requerido('Administrador', 'Compras')
def listar():
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
    return render_template('inventario/listar.html', productos=productos)


@bp.route('/informe-proteinas')
@login_required
@rol_requerido('Administrador', 'Compras')
def informe_proteinas():
    """Resumen de compras y salidas por venta de productos tipo proteina."""
    from datetime import datetime

    fecha_desde = request.args.get('desde', '')
    fecha_hasta = request.args.get('hasta', '')

    try:
        desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date() if fecha_desde else None
        hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date() if fecha_hasta else None
    except ValueError:
        flash('Las fechas seleccionadas no son validas.', 'warning')
        return redirect(url_for('inventario.informe_proteinas'))

    proteinas = Producto.query.filter(
        db.func.upper(Producto.nombre).like('%PROTEINA%')
    ).order_by(Producto.nombre).all()
    proteina_ids = {producto.id for producto in proteinas}
    resumen = {
        producto.id: {
            'nombre': producto.nombre,
            'unidad': producto.unidad_medida,
            'compras': Decimal('0'),
            'costo_compras': Decimal('0'),
            'ventas': Decimal('0')
        }
        for producto in proteinas
    }

    if proteina_ids:
        compras_query = Compra.query.filter(Compra.producto_id.in_(proteina_ids))
        if desde:
            compras_query = compras_query.filter(Compra.fecha >= desde)
        if hasta:
            compras_query = compras_query.filter(Compra.fecha <= hasta)
        for compra in compras_query.all():
            resumen[compra.producto_id]['compras'] += compra.cantidad
            resumen[compra.producto_id]['costo_compras'] += compra.costo_total

    ventas_query = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        VentaDetalle.es_cortesia == False
    )
    if desde:
        ventas_query = ventas_query.filter(VentaDiaria.fecha >= desde)
    if hasta:
        ventas_query = ventas_query.filter(VentaDiaria.fecha <= hasta)

    for detalle in ventas_query.all():
        # Una proteina puede venderse directamente o consumirse por la receta del plato vendido.
        if detalle.producto_id in proteina_ids:
            resumen[detalle.producto_id]['ventas'] += Decimal(str(detalle.cantidad))
        for ingrediente in detalle.producto.receta:
            if ingrediente.insumo_id in proteina_ids:
                resumen[ingrediente.insumo_id]['ventas'] += ingrediente.cantidad * detalle.cantidad

    filas = [datos for datos in resumen.values()
             if datos['compras'] > 0 or datos['ventas'] > 0]
    filas.sort(key=lambda datos: datos['nombre'])

    return render_template(
        'inventario/informe_proteinas.html',
        filas=filas,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total_compras=sum((fila['compras'] for fila in filas), Decimal('0')),
        total_ventas=sum((fila['ventas'] for fila in filas), Decimal('0')),
        total_costo=sum((fila['costo_compras'] for fila in filas), Decimal('0'))
    )


# ============================================================
# COMPROBANTES DE COMPRA
# ============================================================

@bp.route('/compras')
@login_required
@rol_requerido('Administrador', 'Compras')
def compras():
    comprobantes = ComprobanteCompra.query.order_by(ComprobanteCompra.fecha.desc()).limit(50).all()
    return render_template('inventario/compras.html', comprobantes=comprobantes)


@bp.route('/compras/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def nuevo_comprobante():
    """Crear un nuevo comprobante de compra y agregar items."""
    form_comprobante = ComprobanteForm()
    form_item = CompraItemForm()
    form_item.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.filter_by(activa=True, visible_compras=True).order_by(Categoria.nombre).all()]
    form_item.producto_id.choices = [(p.id, f"{p.nombre} ({p.unidad_medida})") for p in Producto.query.filter(
        Producto.activo == True, Producto.tipo == 'producto'
    ).order_by(Producto.nombre).all()]

    # Buscar comprobante en proceso (sin finalizar)
    comprobante = ComprobanteCompra.query.filter_by(
        usuario_id=current_user.id, total=0
    ).order_by(ComprobanteCompra.id.desc()).first()

    if not comprobante:
        # Crear uno nuevo
        comprobante = ComprobanteCompra(
            fecha=date.today(),
            usuario_id=current_user.id,
            forma_pago='Caja General',
            total=0
        )
        db.session.add(comprobante)
        db.session.commit()

    # Items del comprobante actual
    items = Compra.query.filter_by(comprobante_id=comprobante.id).all()
    total_items = sum(c.costo_total for c in items)

    return render_template('inventario/comprobante_form.html',
                           comprobante=comprobante,
                           form_comprobante=form_comprobante,
                           form_item=form_item,
                           items=items,
                           total_items=total_items)


@bp.route('/compras/agregar-item/<int:comprobante_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def agregar_item_compra(comprobante_id):
    """Agregar un item al comprobante."""
    comprobante = ComprobanteCompra.query.get_or_404(comprobante_id)

    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', type=float)
    costo_total = request.form.get('costo_total', type=float)
    categoria_id = request.form.get('categoria_id', type=int)

    if not producto_id or not cantidad or not costo_total:
        flash('Datos incompletos.', 'danger')
        return redirect(url_for('inventario.nuevo_comprobante'))

    producto = Producto.query.get(producto_id)
    compra = Compra(
        producto_id=producto_id,
        categoria_id=categoria_id,
        comprobante_id=comprobante.id,
        cantidad=Decimal(str(cantidad)),
        costo_total=Decimal(str(costo_total)),
        fecha=comprobante.fecha,
        usuario_id=current_user.id
    )

    # Si maneja inventario, actualizar stock
    if producto.maneja_inventario:
        producto.stock_actual += Decimal(str(cantidad))

    db.session.add(compra)
    db.session.commit()
    flash(f'{producto.nombre} x{cantidad} agregado.', 'success')
    return redirect(url_for('inventario.nuevo_comprobante'))


@bp.route('/compras/eliminar-item/<int:compra_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def eliminar_item_compra(compra_id):
    """Eliminar un item del comprobante."""
    compra = Compra.query.get_or_404(compra_id)
    producto = compra.producto
    if producto and producto.maneja_inventario:
        producto.stock_actual -= compra.cantidad
    db.session.delete(compra)
    db.session.commit()
    flash('Item eliminado.', 'success')
    return redirect(url_for('inventario.nuevo_comprobante'))


@bp.route('/compras/finalizar/<int:comprobante_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def finalizar_comprobante(comprobante_id):
    """Finalizar el comprobante de compra."""
    comprobante = ComprobanteCompra.query.get_or_404(comprobante_id)

    proveedor = request.form.get('proveedor', '').strip()
    forma_pago = request.form.get('forma_pago', 'Caja General')
    observacion = request.form.get('observacion', '').strip()

    items = Compra.query.filter_by(comprobante_id=comprobante.id).all()
    if not items:
        flash('No hay items en el comprobante.', 'danger')
        return redirect(url_for('inventario.nuevo_comprobante'))

    total = sum(c.costo_total for c in items)
    comprobante.proveedor = proveedor
    comprobante.forma_pago = forma_pago
    comprobante.observacion = observacion
    comprobante.total = total

    # Si es Caja Menor, descontar del saldo
    if forma_pago == 'Caja Menor':
        caja = CajaMenor.query.first()
        if caja:
            if total > caja.saldo_actual:
                flash(f'Saldo insuficiente en Caja Menor (${caja.saldo_actual:,.0f}). Total: ${total:,.0f}', 'danger')
                return redirect(url_for('inventario.nuevo_comprobante'))
            caja.saldo_actual -= total
            mov = MovimientoCajaMenor(
                caja_menor_id=caja.id,
                fecha=comprobante.fecha,
                tipo='compra',
                monto=total,
                descripcion=f'Comprobante #{comprobante.id} - {proveedor or "Sin proveedor"}',
                comprobante_id=comprobante.id,
                usuario_id=current_user.id
            )
            db.session.add(mov)

    db.session.commit()
    flash(f'Comprobante #{comprobante.id} finalizado. Total: ${total:,.0f} ({forma_pago})', 'success')
    return redirect(url_for('inventario.compras'))


@bp.route('/compras/ver/<int:id>')
@login_required
@rol_requerido('Administrador', 'Compras')
def ver_comprobante(id):
    comprobante = ComprobanteCompra.query.get_or_404(id)
    items = Compra.query.filter_by(comprobante_id=comprobante.id).all()
    return render_template('inventario/ver_comprobante.html', comprobante=comprobante, items=items)


# ============================================================
# CAJA MENOR
# ============================================================

@bp.route('/caja-menor')
@login_required
@rol_requerido('Administrador', 'Compras')
def caja_menor():
    caja = CajaMenor.query.first()
    movimientos = MovimientoCajaMenor.query.order_by(MovimientoCajaMenor.fecha.desc()).limit(30).all()
    return render_template('inventario/caja_menor.html', caja=caja, movimientos=movimientos, today=date.today().strftime('%Y-%m-%d'))


@bp.route('/caja-menor/abastecer', methods=['POST'])
@login_required
@rol_requerido('Administrador')
def abastecer_caja_menor():
    """Abastecer la caja menor (solo Administrador)."""
    from datetime import datetime
    caja = CajaMenor.query.first()
    monto = request.form.get('monto', type=float)
    descripcion = request.form.get('descripcion', '').strip()
    fecha_str = request.form.get('fecha')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()

    if not monto or monto <= 0:
        flash('Monto inválido.', 'danger')
        return redirect(url_for('inventario.caja_menor'))

    monto_decimal = Decimal(str(monto))
    nuevo_saldo = caja.saldo_actual + monto_decimal

    if nuevo_saldo > caja.tope:
        flash(f'El abastecimiento excede el tope (${caja.tope:,.0f}). Saldo actual: ${caja.saldo_actual:,.0f}', 'danger')
        return redirect(url_for('inventario.caja_menor'))

    caja.saldo_actual = nuevo_saldo
    mov = MovimientoCajaMenor(
        caja_menor_id=caja.id,
        fecha=fecha,
        tipo='abastecimiento',
        monto=monto_decimal,
        descripcion=descripcion or 'Abastecimiento de caja menor',
        usuario_id=current_user.id
    )
    db.session.add(mov)
    db.session.commit()
    flash(f'Caja menor abastecida con ${monto:,.0f}. Saldo: ${caja.saldo_actual:,.0f}', 'success')
    return redirect(url_for('inventario.caja_menor'))


@bp.route('/caja-menor/configurar-tope', methods=['POST'])
@login_required
@rol_requerido('Administrador')
def configurar_tope_caja_menor():
    """Configurar el tope de la caja menor."""
    caja = CajaMenor.query.first()
    tope = request.form.get('tope', type=float)
    if tope and tope > 0:
        caja.tope = Decimal(str(tope))
        db.session.commit()
        flash(f'Tope actualizado a ${tope:,.0f}', 'success')
    return redirect(url_for('inventario.caja_menor'))


# ============================================================
# API: Productos por categoría (para filtrar en compras)
# ============================================================

@bp.route('/api/productos-por-categoria/<int:categoria_id>')
@login_required
def productos_por_categoria(categoria_id):
    """Devuelve productos de una categoría que se pueden comprar."""
    productos = Producto.query.filter(
        Producto.activo == True,
        Producto.tipo == 'producto',
        Producto.categoria_id == categoria_id,
        db.or_(Producto.maneja_inventario == True, Producto.se_vende == False)
    ).order_by(Producto.nombre).all()
    return jsonify([{'id': p.id, 'nombre': f"{p.nombre} ({p.unidad_medida})"} for p in productos])


# ============================================================
# AJUSTE DE INVENTARIO (carga inicial / conteo físico)
# ============================================================

def _registrar_ajuste_producto(producto, cantidad_nueva, usuario_id, valor=Decimal('0'),
                               tipo='ajuste_conteo', motivo='Ajuste por conteo fÃ­sico'):
    """Crear el registro de ajuste y actualizar el stock si hubo cambio."""
    if cantidad_nueva == producto.stock_actual:
        return False

    ajuste = AjusteInventario(
        fecha=date.today(),
        producto_id=producto.id,
        tipo=tipo,
        cantidad_anterior=producto.stock_actual,
        cantidad_nueva=cantidad_nueva,
        diferencia=cantidad_nueva - producto.stock_actual,
        valor=valor,
        motivo=motivo,
        usuario_id=usuario_id
    )
    db.session.add(ajuste)
    producto.stock_actual = cantidad_nueva
    return True


@bp.route('/ajuste')
@login_required
@rol_requerido('Administrador', 'Compras')
def ajuste_inventario():
    """Pantalla para ajustar saldos de inventario (carga inicial o conteo)."""
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
    return render_template('inventario/ajuste.html', productos=productos)


@bp.route('/ajuste/guardar', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def guardar_ajuste():
    """Guardar ajuste de inventario para múltiples productos."""
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).all()
    ajustes_realizados = 0

    for prod in productos:
        cantidad_str = request.form.get(f'cantidad_{prod.id}')
        valor_str = request.form.get(f'valor_{prod.id}')

        if cantidad_str:
            try:
                cantidad_nueva = Decimal(cantidad_str)
            except:
                continue

            valor = Decimal(valor_str) if valor_str else Decimal('0')

            if cantidad_nueva != prod.stock_actual:
                ajuste = AjusteInventario(
                    fecha=date.today(),
                    producto_id=prod.id,
                    tipo='ajuste_conteo',
                    cantidad_anterior=prod.stock_actual,
                    cantidad_nueva=cantidad_nueva,
                    diferencia=cantidad_nueva - prod.stock_actual,
                    valor=valor,
                    motivo='Ajuste por conteo físico',
                    usuario_id=current_user.id
                )
                db.session.add(ajuste)
                prod.stock_actual = cantidad_nueva
                ajustes_realizados += 1

    db.session.commit()
    if ajustes_realizados > 0:
        flash(f'Inventario ajustado: {ajustes_realizados} producto(s) actualizados.', 'success')
    else:
        flash('No hubo cambios en el inventario.', 'info')
    return redirect(url_for('inventario.ajuste_inventario'))


@bp.route('/ajuste/poner-cero', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def poner_inventario_en_cero():
    """Dejar en cero todos los productos que manejan inventario."""
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).all()
    ajustes_realizados = 0

    for prod in productos:
        if _registrar_ajuste_producto(
            prod,
            Decimal('0'),
            current_user.id,
            tipo='ajuste_conteo',
            motivo='Inventario reiniciado a cero'
        ):
            ajustes_realizados += 1

    db.session.commit()
    if ajustes_realizados > 0:
        flash(f'Inventario en cero: {ajustes_realizados} producto(s) actualizados.', 'success')
    else:
        flash('Todos los productos ya estaban en cero.', 'info')
    return redirect(url_for('inventario.ajuste_inventario'))


# ============================================================
# MERMA / DESPERDICIO
# ============================================================

@bp.route('/merma')
@login_required
@rol_requerido('Administrador', 'Compras')
def merma():
    """Registrar merma o desperdicio."""
    productos = Producto.query.filter_by(activo=True, maneja_inventario=True).order_by(Producto.nombre).all()
    # Últimas mermas registradas
    ultimas_mermas = AjusteInventario.query.filter_by(tipo='merma').order_by(AjusteInventario.fecha.desc()).limit(20).all()
    return render_template('inventario/merma.html', productos=productos, ultimas_mermas=ultimas_mermas)


@bp.route('/merma/registrar', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Compras')
def registrar_merma():
    """Registrar una merma/desperdicio."""
    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', type=float)
    motivo = request.form.get('motivo', '').strip()

    if not producto_id or not cantidad or cantidad <= 0:
        flash('Datos incompletos.', 'danger')
        return redirect(url_for('inventario.merma'))

    if not motivo:
        flash('Debe indicar el motivo de la merma.', 'danger')
        return redirect(url_for('inventario.merma'))

    producto = Producto.query.get_or_404(producto_id)
    cantidad_decimal = Decimal(str(cantidad))

    ajuste = AjusteInventario(
        fecha=date.today(),
        producto_id=producto.id,
        tipo='merma',
        cantidad_anterior=producto.stock_actual,
        cantidad_nueva=producto.stock_actual - cantidad_decimal,
        diferencia=-cantidad_decimal,
        valor=Decimal('0'),
        motivo=motivo,
        usuario_id=current_user.id
    )
    producto.stock_actual -= cantidad_decimal

    db.session.add(ajuste)
    db.session.commit()
    flash(f'Merma registrada: {producto.nombre} -{cantidad} ({motivo}). Stock: {producto.stock_actual}', 'success')
    return redirect(url_for('inventario.merma'))
