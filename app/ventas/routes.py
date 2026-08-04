from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.ventas import bp
from app.ventas.forms import VentaDetalleForm, DescuentoAlmuerzosForm, CierreCajaForm, AbrirDiaForm
from app.models import (VentaDiaria, VentaDetalle, Producto, Categoria,
                        FormaPago, Persona, Credito, PagoElectronico, PagoCredito,
                        Compra)
from app.decorators import rol_requerido
from datetime import date
from decimal import Decimal


def obtener_forma_pago_credito(observacion):
    """Extrae la forma de pago de la observación del PagoCredito."""
    if observacion and '|' in observacion:
        return observacion.split('|')[1]
    return 'Efectivo'  # Default si no tiene formato


def obtener_venta_abierta():
    """Busca la venta diaria abierta (hoy o la última no cerrada)."""
    hoy = date.today()
    venta_dia = VentaDiaria.query.filter_by(fecha=hoy, estado='abierto').first()
    if not venta_dia:
        venta_dia = VentaDiaria.query.filter(
            VentaDiaria.estado == 'abierto'
        ).order_by(VentaDiaria.fecha.desc()).first()
    return venta_dia


@bp.route('/')
@login_required
@rol_requerido('Administrador', 'Caja')
def index():
    venta_dia = obtener_venta_abierta()

    if not venta_dia:
        # Buscar si hay cerradas por caja pendientes de validar
        pendiente = VentaDiaria.query.filter_by(estado='cerrado_caja').order_by(VentaDiaria.fecha.desc()).first()
        if pendiente:
            return redirect(url_for('ventas.ver_cierre', id=pendiente.id))
        form = AbrirDiaForm()
        return render_template('ventas/abrir_dia.html', form=form)

    # Cargar datos para el registro
    categorias = Categoria.query.filter_by(activa=True, visible_ventas=True).order_by(Categoria.nombre).all()
    personas = Persona.query.filter_by(activa=True).order_by(Persona.nombre).all()

    # Productos agrupados por categoría
    productos_por_cat = {}
    for cat in categorias:
        productos_por_cat[cat.id] = Producto.query.filter_by(
            categoria_id=cat.id, activo=True, se_vende=True
        ).order_by(Producto.nombre).all()

    # Detalles del día
    detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).all()

    # Resumen por categoría
    resumen_categorias = {}
    for cat in categorias:
        cat_items = [d for d in detalles if d.producto.categoria_id == cat.id and not d.es_cortesia]
        cortesias = [d for d in detalles if d.producto.categoria_id == cat.id and d.es_cortesia]
        resumen_categorias[cat.id] = {
            'nombre': cat.nombre,
            'detalles': cat_items,
            'cortesias': cortesias,
            'total_cantidad': sum(d.cantidad for d in cat_items),
            'total_dinero': sum(d.subtotal for d in cat_items)
        }

    total_ventas = sum(d.subtotal for d in detalles if not d.es_cortesia)
    descuento = venta_dia.descuento_almuerzos or Decimal('0')
    total_neto = total_ventas - descuento

    # Última categoría usada (para recordar)
    ultima_categoria = request.args.get('cat', type=int)
    if not ultima_categoria and detalles:
        ultima_categoria = detalles[-1].producto.categoria_id

    # Créditos pendientes para recibir pagos
    creditos_pendientes = Credito.query.filter(
        Credito.estado.in_(['pendiente', 'abonado'])
    ).order_by(Credito.fecha).all()

    # Pagos de créditos recibidos hoy
    pagos_creditos_hoy = PagoCredito.query.filter_by(fecha=venta_dia.fecha).all()
    total_pagos_creditos_hoy = sum(p.monto for p in pagos_creditos_hoy)

    # Créditos otorgados hoy (para mostrar y permitir eliminar)
    creditos_hoy = Credito.query.filter_by(fecha=venta_dia.fecha).all()

    return render_template('ventas/index.html',
                           venta_dia=venta_dia,
                           categorias=categorias,
                           productos_por_cat=productos_por_cat,
                           resumen_categorias=resumen_categorias,
                           detalles=detalles,
                           total_ventas=total_ventas,
                           descuento_almuerzos=descuento,
                           total_neto=total_neto,
                           personas=personas,
                           ultima_categoria=ultima_categoria,
                           creditos_pendientes=creditos_pendientes,
                           pagos_creditos_hoy=pagos_creditos_hoy,
                           total_pagos_creditos_hoy=total_pagos_creditos_hoy,
                           creditos_hoy=creditos_hoy)


@bp.route('/abrir', methods=['POST'])
@login_required
def abrir_dia():
    form = AbrirDiaForm()
    if form.validate_on_submit():
        fecha = form.fecha.data
        existente = VentaDiaria.query.filter_by(fecha=fecha).first()
        if existente:
            flash('Ya existe un registro para esa fecha.', 'warning')
            return redirect(url_for('ventas.index'))
        venta_dia = VentaDiaria(fecha=fecha, usuario_id=current_user.id, estado='abierto')
        db.session.add(venta_dia)
        db.session.commit()
        flash(f'Dia {fecha.strftime("%d/%m/%Y")} abierto para registro de ventas.', 'success')
    else:
        hoy = date.today()
        existente = VentaDiaria.query.filter_by(fecha=hoy).first()
        if not existente:
            venta_dia = VentaDiaria(fecha=hoy, usuario_id=current_user.id, estado='abierto')
            db.session.add(venta_dia)
            db.session.commit()
            flash(f'Dia {hoy.strftime("%d/%m/%Y")} abierto.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/eliminar-dia', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Caja')
def eliminar_dia():
    """Eliminar un día abierto sin ventas registradas."""
    venta_dia = obtener_venta_abierta()
    if not venta_dia:
        flash('No hay un día abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).count()
    if detalles > 0:
        flash('No se puede eliminar: el día tiene ventas registradas.', 'danger')
        return redirect(url_for('ventas.index'))

    db.session.delete(venta_dia)
    db.session.commit()
    flash('Día eliminado.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/agregar', methods=['POST'])
@login_required
def agregar_venta():
    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No hay un dia abierto para registrar ventas.', 'danger')
        return redirect(url_for('ventas.index'))

    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', 1, type=int)

    if not producto_id or cantidad < 1:
        flash('Datos invalidos.', 'danger')
        return redirect(url_for('ventas.index'))

    producto = Producto.query.get(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('ventas.index'))

    precio_unitario = producto.precio
    subtotal = precio_unitario * cantidad

    detalle = VentaDetalle(
        venta_diaria_id=venta_dia.id,
        producto_id=producto.id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        descuento=Decimal('0'),
        subtotal=subtotal,
        es_credito=False,
        es_cortesia=False
    )
    db.session.add(detalle)
    db.session.commit()

    flash(f'{producto.nombre} x{cantidad} agregado.', 'success')
    return redirect(url_for('ventas.index', cat=producto.categoria_id))


@bp.route('/cortesia', methods=['POST'])
@login_required
def agregar_cortesia():
    """Registrar cortesía (solo almuerzos)."""
    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No hay un dia abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', 1, type=int)
    persona_id = request.form.get('persona_id', type=int)

    producto = Producto.query.get(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('ventas.index'))

    # Verificar que sea almuerzo
    cat_almuerzos = Categoria.query.filter_by(nombre='Almuerzos').first()
    if not cat_almuerzos or producto.categoria_id != cat_almuerzos.id:
        flash('Las cortesias solo aplican para almuerzos.', 'warning')
        return redirect(url_for('ventas.index'))

    detalle = VentaDetalle(
        venta_diaria_id=venta_dia.id,
        producto_id=producto.id,
        cantidad=cantidad,
        precio_unitario=producto.precio,
        descuento=Decimal('0'),
        subtotal=Decimal('0'),  # Cortesía no suma dinero
        es_credito=False,
        es_cortesia=True,
        cliente_credito_id=persona_id if persona_id else None
    )
    db.session.add(detalle)
    db.session.commit()

    persona_nombre = ''
    if persona_id:
        persona = Persona.query.get(persona_id)
        persona_nombre = f' para {persona.nombre}' if persona else ''
    flash(f'Cortesia: {producto.nombre} x{cantidad}{persona_nombre}', 'success')
    return redirect(url_for('ventas.index', cat=producto.categoria_id))


@bp.route('/descuento', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Caja')
def aplicar_descuento():
    """Aplicar descuento al total de almuerzos."""
    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No hay un dia abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    descuento = request.form.get('descuento', 0, type=float)
    justificacion = request.form.get('justificacion', '').strip()

    if descuento > 0 and not justificacion:
        flash('Debe justificar el descuento.', 'danger')
        return redirect(url_for('ventas.index'))

    venta_dia.descuento_almuerzos = Decimal(str(descuento))
    venta_dia.justificacion_descuento = justificacion
    db.session.commit()
    flash(f'Descuento de ${descuento:,.0f} aplicado.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/recibir-pago-credito', methods=['POST'])
@login_required
def recibir_pago_credito():
    """Recibir pago de un crédito pendiente. Suma al día y resta del crédito."""
    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No hay un dia abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    credito_id = request.form.get('credito_id', type=int)
    monto_pago = request.form.get('monto_pago', type=float)
    forma_pago = request.form.get('forma_pago', 'Efectivo')

    if not credito_id or not monto_pago or monto_pago <= 0:
        flash('Datos incompletos.', 'danger')
        return redirect(url_for('ventas.index'))

    credito = Credito.query.get(credito_id)
    if not credito:
        flash('Credito no encontrado.', 'danger')
        return redirect(url_for('ventas.index'))

    monto = Decimal(str(monto_pago))
    if monto > credito.saldo_pendiente:
        flash(f'El monto excede el saldo pendiente (${credito.saldo_pendiente:,.0f}).', 'danger')
        return redirect(url_for('ventas.index'))

    # Registrar el pago
    pago = PagoCredito(
        credito_id=credito.id,
        fecha=venta_dia.fecha,
        monto=monto,
        observacion=f'Pago {venta_dia.fecha.strftime("%d/%m/%Y")}|{forma_pago}'
    )
    db.session.add(pago)

    # Actualizar saldo del crédito
    credito.saldo_pendiente -= monto
    if credito.saldo_pendiente <= 0:
        credito.saldo_pendiente = Decimal('0')
        credito.estado = 'cancelado'
    else:
        credito.estado = 'abonado'

    db.session.commit()
    flash(f'Pago de ${monto:,.0f} ({forma_pago}) recibido de {credito.persona.nombre}. Saldo: ${credito.saldo_pendiente:,.0f}', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_detalle(id):
    detalle = VentaDetalle.query.get_or_404(id)
    venta_dia = detalle.venta_diaria

    if venta_dia.estado != 'abierto':
        flash('No se puede modificar un dia cerrado.', 'danger')
        return redirect(url_for('ventas.index'))

    cat_id = detalle.producto.categoria_id
    db.session.delete(detalle)
    db.session.commit()
    flash('Item eliminado.', 'success')
    return redirect(url_for('ventas.index', cat=cat_id))


@bp.route('/anular-pago-credito/<int:pago_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Caja')
def anular_pago_credito(pago_id):
    """Anular un pago de crédito recibido hoy (devuelve saldo al crédito)."""
    pago = PagoCredito.query.get_or_404(pago_id)
    credito = pago.credito

    # Verificar que el día esté abierto
    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No se puede anular: el día no está abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    # Devolver saldo al crédito
    credito.saldo_pendiente += pago.monto
    if credito.saldo_pendiente > 0:
        credito.estado = 'abonado' if credito.saldo_pendiente < credito.monto_total else 'pendiente'

    nombre = credito.persona.nombre
    monto = pago.monto

    db.session.delete(pago)
    db.session.commit()
    flash(f'Pago de ${monto:,.0f} de {nombre} anulado. Saldo devuelto al crédito.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/eliminar-credito/<int:credito_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Caja')
def eliminar_credito_dia(credito_id):
    """Eliminar un crédito registrado hoy (antes de cerrar caja)."""
    credito = Credito.query.get_or_404(credito_id)

    venta_dia = obtener_venta_abierta()
    if not venta_dia or venta_dia.estado != 'abierto':
        flash('No se puede eliminar: el día no está abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    nombre = credito.persona.nombre
    monto = credito.monto_total

    # Eliminar pagos asociados si los tiene
    PagoCredito.query.filter_by(credito_id=credito.id).delete()
    db.session.delete(credito)
    db.session.commit()
    flash(f'Crédito de ${monto:,.0f} de {nombre} eliminado.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/cerrar-caja', methods=['GET', 'POST'])
@login_required
def cerrar_caja():
    """Cierre parcial por cajero: indica desglose de formas de pago."""
    venta_dia = obtener_venta_abierta()
    if not venta_dia:
        flash('No hay un dia abierto.', 'danger')
        return redirect(url_for('ventas.index'))

    detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).all()
    total_ventas = sum(d.subtotal for d in detalles if not d.es_cortesia)
    descuento = venta_dia.descuento_almuerzos or Decimal('0')
    total_neto = total_ventas - descuento

    # Pagos electrónicos ya registrados
    pagos = PagoElectronico.query.filter_by(venta_diaria_id=venta_dia.id).all()
    total_pagos_elec = sum(p.monto for p in pagos)

    # Créditos del día
    creditos_dia = Credito.query.filter_by(fecha=venta_dia.fecha).all()
    total_creditos = sum(c.monto_total for c in creditos_dia)

    # Personas para el formulario de créditos
    personas = Persona.query.filter(
        Persona.activa == True,
        Persona.tipo.in_(['credito', 'ambos'])
    ).order_by(Persona.nombre).all()

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'agregar_pago':
            plataforma = request.form.get('plataforma')
            monto = request.form.get('monto', type=float)
            referencia = request.form.get('referencia', '').strip()
            titular = request.form.get('titular', '').strip()

            if plataforma and monto and monto > 0:
                pago = PagoElectronico(
                    venta_diaria_id=venta_dia.id,
                    plataforma=plataforma,
                    monto=Decimal(str(monto)),
                    referencia=referencia,
                    titular=titular
                )
                db.session.add(pago)
                db.session.commit()
                flash(f'Pago {plataforma} ${monto:,.0f} registrado.', 'success')
            else:
                flash('Datos de pago incompletos.', 'danger')
            return redirect(url_for('ventas.cerrar_caja'))

        elif accion == 'eliminar_pago':
            pago_id = request.form.get('pago_id', type=int)
            pago = PagoElectronico.query.get(pago_id)
            if pago:
                db.session.delete(pago)
                db.session.commit()
                flash('Pago eliminado.', 'success')
            return redirect(url_for('ventas.cerrar_caja'))

        elif accion == 'agregar_credito':
            persona_id = request.form.get('persona_id', type=int)
            monto_credito = request.form.get('monto_credito', type=float)
            obs_credito = request.form.get('obs_credito', '').strip()

            if persona_id and monto_credito and monto_credito > 0:
                credito = Credito(
                    persona_id=persona_id,
                    monto_total=Decimal(str(monto_credito)),
                    saldo_pendiente=Decimal(str(monto_credito)),
                    fecha=venta_dia.fecha,
                    observacion=obs_credito or f'Credito del {venta_dia.fecha.strftime("%d/%m/%Y")}',
                    estado='pendiente'
                )
                db.session.add(credito)
                db.session.commit()
                flash(f'Credito de ${monto_credito:,.0f} registrado.', 'success')
            else:
                flash('Indica el cliente y el valor del credito.', 'danger')
            return redirect(url_for('ventas.cerrar_caja'))

        elif accion == 'eliminar_credito':
            credito_id = request.form.get('credito_id', type=int)
            credito = Credito.query.get(credito_id)
            if credito:
                db.session.delete(credito)
                db.session.commit()
                flash('Credito eliminado.', 'success')
            return redirect(url_for('ventas.cerrar_caja'))

        elif accion == 'cerrar':
            # Recalcular totales de ventas del día
            pagos = PagoElectronico.query.filter_by(venta_diaria_id=venta_dia.id).all()
            creditos_dia = Credito.query.filter_by(fecha=venta_dia.fecha).all()

            total_pagos_elec = sum(p.monto for p in pagos)
            total_creditos = sum(c.monto_total for c in creditos_dia)
            total_efectivo_ventas = total_neto - total_pagos_elec - total_creditos

            total_nequi = sum(p.monto for p in pagos if p.plataforma == 'Nequi')
            total_daviplata = sum(p.monto for p in pagos if p.plataforma == 'Daviplata')
            total_transferencia = sum(p.monto for p in pagos if p.plataforma == 'Cuenta')

            # Pagos de créditos de otros días recibidos hoy
            pagos_cred_hoy = PagoCredito.query.filter_by(fecha=venta_dia.fecha).all()
            efectivo_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Efectivo')
            nequi_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Nequi')
            daviplata_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Daviplata')
            cuenta_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Cuenta')

            venta_dia.total_ventas = total_neto
            venta_dia.total_efectivo = (total_efectivo_ventas if total_efectivo_ventas > 0 else Decimal('0')) + efectivo_otros
            venta_dia.total_nequi = total_nequi + nequi_otros
            venta_dia.total_daviplata = total_daviplata + daviplata_otros
            venta_dia.total_transferencia = total_transferencia + cuenta_otros
            venta_dia.total_credito = total_creditos
            venta_dia.estado = 'cerrado_caja'
            venta_dia.cerrada = True

            # Calcular descuentos por producto antes de aplicarlos
            from app.models import MovimientoInventario, Receta
            descuentos_por_producto = {}
            for d in detalles:
                producto = d.producto
                # Si el producto maneja inventario directo, descontarse a sí mismo
                if producto.maneja_inventario:
                    descuentos_por_producto[producto.id] = descuentos_por_producto.get(producto.id, Decimal('0')) + d.cantidad
                # Receta: descontar los ingredientes
                for r in producto.receta:
                    if r.insumo.maneja_inventario:
                        descuentos_por_producto[r.insumo_id] = descuentos_por_producto.get(r.insumo_id, Decimal('0')) + (r.cantidad * d.cantidad)

            # Compras del día por producto
            compras_dia_list = Compra.query.filter_by(fecha=venta_dia.fecha).all()
            compras_por_producto = {}
            for c in compras_dia_list:
                if c.producto and c.producto.maneja_inventario:
                    compras_por_producto[c.producto_id] = compras_por_producto.get(c.producto_id, Decimal('0')) + c.cantidad

            # Registrar movimientos y descontar inventario
            todos_ids = set(list(descuentos_por_producto.keys()) + list(compras_por_producto.keys()))
            for prod_id in todos_ids:
                prod = Producto.query.get(prod_id)
                if not prod or not prod.maneja_inventario:
                    continue

                ventas_cant = descuentos_por_producto.get(prod_id, Decimal('0'))
                compras_cant = compras_por_producto.get(prod_id, Decimal('0'))

                # stock_actual ya incluye las compras del día (se sumaron al registrarlas)
                # Saldo inicio = stock_actual - compras_dia (antes de comprar)
                saldo_inicio = prod.stock_actual - compras_cant
                subtotal = saldo_inicio + compras_cant  # = prod.stock_actual
                saldo_final = subtotal - ventas_cant

                # Registrar foto del movimiento
                mov_existente = MovimientoInventario.query.filter_by(
                    fecha=venta_dia.fecha, producto_id=prod_id
                ).first()
                if not mov_existente:
                    mov = MovimientoInventario(
                        fecha=venta_dia.fecha,
                        producto_id=prod_id,
                        saldo_inicio=saldo_inicio,
                        compras=compras_cant,
                        ventas=ventas_cant,
                        saldo_final=saldo_final
                    )
                    db.session.add(mov)

                prod.stock_actual = saldo_final

            db.session.commit()
            flash(f'Caja cerrada. Total: ${total_neto:,.0f} | Efectivo: ${total_efectivo_ventas:,.0f}', 'success')
            return redirect(url_for('ventas.ver_cierre', id=venta_dia.id))

    # Agrupar pagos por plataforma
    resumen_pagos = {'Nequi': [], 'Daviplata': [], 'Cuenta': []}
    for p in pagos:
        if p.plataforma in resumen_pagos:
            resumen_pagos[p.plataforma].append(p)

    # Pagos de créditos recibidos hoy
    pagos_creditos_hoy = PagoCredito.query.filter_by(fecha=venta_dia.fecha).all()
    total_pagos_creditos_hoy = sum(p.monto for p in pagos_creditos_hoy)

    return render_template('ventas/cerrar_caja.html',
                           venta_dia=venta_dia,
                           total_ventas=total_ventas,
                           descuento=descuento,
                           total_neto=total_neto,
                           pagos=pagos,
                           resumen_pagos=resumen_pagos,
                           total_pagos_elec=total_pagos_elec,
                           creditos_dia=creditos_dia,
                           total_creditos=total_creditos,
                           personas=personas,
                           pagos_creditos_hoy=pagos_creditos_hoy,
                           total_pagos_creditos_hoy=total_pagos_creditos_hoy)


@bp.route('/cierre/<int:id>')
@login_required
def ver_cierre(id):
    venta_dia = VentaDiaria.query.get_or_404(id)
    detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).all()
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()

    resumen = {}
    for cat in categorias:
        cat_items = [d for d in detalles if d.producto.categoria_id == cat.id and not d.es_cortesia]
        cortesias = [d for d in detalles if d.producto.categoria_id == cat.id and d.es_cortesia]
        if cat_items or cortesias:
            resumen[cat.nombre] = {
                'detalles': cat_items,
                'cortesias': cortesias,
                'total_cantidad': sum(d.cantidad for d in cat_items),
                'total_dinero': sum(d.subtotal for d in cat_items)
            }

    # Pagos de créditos de otros días recibidos este día
    pagos_cred_hoy = PagoCredito.query.filter_by(fecha=venta_dia.fecha).all()
    total_pagos_cred = sum(p.monto for p in pagos_cred_hoy)

    # Desglose por forma de pago de pagos de créditos
    efectivo_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Efectivo')
    nequi_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Nequi')
    daviplata_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Daviplata')
    cuenta_otros = sum(p.monto for p in pagos_cred_hoy if obtener_forma_pago_credito(p.observacion) == 'Cuenta')

    # Efectivo de ventas del día (sin otros días)
    descuento = venta_dia.descuento_almuerzos or Decimal('0')
    total_ventas_bruto = sum(d.subtotal for d in detalles if not d.es_cortesia)
    total_neto_ventas = total_ventas_bruto - descuento

    pagos_elec = PagoElectronico.query.filter_by(venta_diaria_id=venta_dia.id).all()
    total_elec_ventas = sum(p.monto for p in pagos_elec)
    creditos_dia = Credito.query.filter_by(fecha=venta_dia.fecha).all()
    total_creditos_dia = sum(c.monto_total for c in creditos_dia)
    efectivo_ventas = total_neto_ventas - total_elec_ventas - total_creditos_dia
    if efectivo_ventas < 0:
        efectivo_ventas = Decimal('0')

    return render_template('ventas/cierre.html',
                           venta_dia=venta_dia,
                           resumen=resumen,
                           pagos_cred_hoy=pagos_cred_hoy,
                           total_pagos_cred=total_pagos_cred,
                           efectivo_ventas=efectivo_ventas,
                           efectivo_otros=efectivo_otros,
                           nequi_otros=nequi_otros,
                           daviplata_otros=daviplata_otros,
                           cuenta_otros=cuenta_otros)


@bp.route('/validar-cierre/<int:id>', methods=['POST'])
@login_required
def validar_cierre(id):
    """Cierre definitivo por el dueño/encargado."""
    venta_dia = VentaDiaria.query.get_or_404(id)
    if venta_dia.estado != 'cerrado_caja':
        flash('Este dia no esta en estado de validacion.', 'warning')
        return redirect(url_for('ventas.historial'))

    venta_dia.estado = 'cerrado_definitivo'
    venta_dia.cerrado_por_id = current_user.id
    db.session.commit()
    flash(f'Dia {venta_dia.fecha.strftime("%d/%m/%Y")} cerrado definitivamente.', 'success')
    return redirect(url_for('ventas.historial'))


@bp.route('/reabrir/<int:id>', methods=['POST'])
@login_required
def reabrir(id):
    """Reabrir un dia cerrado por caja (solo si no es definitivo)."""
    venta_dia = VentaDiaria.query.get_or_404(id)
    if venta_dia.estado == 'cerrado_definitivo':
        flash('No se puede reabrir un dia con cierre definitivo.', 'danger')
        return redirect(url_for('ventas.historial'))

    # Revertir inventario
    detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).all()
    for d in detalles:
        producto = d.producto
        # Si el producto maneja inventario directo
        if producto.maneja_inventario:
            producto.stock_actual += d.cantidad
        # Revertir receta
        for r in producto.receta:
            if r.insumo.maneja_inventario:
                r.insumo.stock_actual += r.cantidad * d.cantidad

    venta_dia.estado = 'abierto'
    venta_dia.cerrada = False
    db.session.commit()
    flash('Dia reabierto. Inventario revertido.', 'success')
    return redirect(url_for('ventas.index'))


@bp.route('/productos/<int:categoria_id>')
@login_required
def productos_por_categoria(categoria_id):
    """API para cargar productos por categoría (AJAX)."""
    productos = Producto.query.filter_by(categoria_id=categoria_id, activo=True).order_by(Producto.nombre).all()
    return jsonify([{'id': p.id, 'nombre': p.nombre, 'precio': float(p.precio)} for p in productos])


@bp.route('/historial')
@login_required
def historial():
    fecha_buscar = request.args.get('fecha')
    if fecha_buscar:
        try:
            from datetime import datetime
            fecha_obj = datetime.strptime(fecha_buscar, '%Y-%m-%d').date()
            venta = VentaDiaria.query.filter_by(fecha=fecha_obj).first()
            if venta:
                return redirect(url_for('ventas.ver_cierre', id=venta.id))
            else:
                flash(f'No hay registro para la fecha {fecha_obj.strftime("%d/%m/%Y")}.', 'warning')
        except ValueError:
            flash('Fecha invalida.', 'danger')

    ventas = VentaDiaria.query.order_by(VentaDiaria.fecha.desc()).limit(30).all()
    return render_template('ventas/historial.html', ventas=ventas)
