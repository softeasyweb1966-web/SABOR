from flask import render_template, request
from flask_login import login_required
from app import db
from app.reportes import bp
from app.models import VentaDiaria, MovimientoInventario, VentaDetalle
from datetime import date


@bp.route('/')
@login_required
def index():
    return render_template('reportes/index.html')


@bp.route('/compras-por-categoria')
@login_required
def compras_por_categoria():
    """Informe de compras agrupado por categoría y producto."""
    from app.models import Compra, Producto, Categoria
    from datetime import datetime

    fecha_desde = request.args.get('desde')
    fecha_hasta = request.args.get('hasta')

    query = Compra.query
    if fecha_desde:
        query = query.filter(Compra.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d').date())
    if fecha_hasta:
        query = query.filter(Compra.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d').date())

    compras = query.order_by(Compra.fecha).all()

    # Agrupar por categoría y producto
    from collections import defaultdict
    resumen = defaultdict(lambda: defaultdict(lambda: {'cantidad': 0, 'costo': 0}))
    totales_cat = defaultdict(lambda: {'cantidad': 0, 'costo': 0})

    for c in compras:
        cat_nombre = c.categoria.nombre if c.categoria else (c.producto.categoria.nombre if c.producto else 'Sin categoría')
        prod_nombre = c.producto.nombre if c.producto else 'Desconocido'
        resumen[cat_nombre][prod_nombre]['cantidad'] += float(c.cantidad)
        resumen[cat_nombre][prod_nombre]['costo'] += float(c.costo_total)
        totales_cat[cat_nombre]['cantidad'] += float(c.cantidad)
        totales_cat[cat_nombre]['costo'] += float(c.costo_total)

    total_general = sum(t['costo'] for t in totales_cat.values())

    return render_template('reportes/compras_categoria.html',
                           resumen=dict(resumen),
                           totales_cat=dict(totales_cat),
                           total_general=total_general,
                           fecha_desde=fecha_desde or '',
                           fecha_hasta=fecha_hasta or '')


@bp.route('/ventas-por-categoria')
@login_required
def ventas_por_categoria():
    """Informe de ventas agrupado por categoría y producto."""
    from app.models import VentaDiaria, VentaDetalle, Producto, Categoria
    from datetime import datetime

    fecha_desde = request.args.get('desde')
    fecha_hasta = request.args.get('hasta')

    query = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        VentaDetalle.es_cortesia == False
    )
    if fecha_desde:
        query = query.filter(VentaDiaria.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d').date())
    if fecha_hasta:
        query = query.filter(VentaDiaria.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d').date())

    detalles = query.all()

    # Agrupar por categoría y producto
    from collections import defaultdict
    resumen = defaultdict(lambda: defaultdict(lambda: {'cantidad': 0, 'valor': 0}))
    totales_cat = defaultdict(lambda: {'cantidad': 0, 'valor': 0})

    for d in detalles:
        cat_nombre = d.producto.categoria.nombre
        prod_nombre = d.producto.nombre
        resumen[cat_nombre][prod_nombre]['cantidad'] += d.cantidad
        resumen[cat_nombre][prod_nombre]['valor'] += float(d.subtotal)
        totales_cat[cat_nombre]['cantidad'] += d.cantidad
        totales_cat[cat_nombre]['valor'] += float(d.subtotal)

    total_general = sum(t['valor'] for t in totales_cat.values())

    return render_template('reportes/ventas_categoria.html',
                           resumen=dict(resumen),
                           totales_cat=dict(totales_cat),
                           total_general=total_general,
                           fecha_desde=fecha_desde or '',
                           fecha_hasta=fecha_hasta or '')
@login_required
def movimientos_inventario():
    """Consulta de movimientos de inventario por día."""
    fecha_str = request.args.get('fecha')
    fecha_sel = None

    if fecha_str:
        try:
            from datetime import datetime
            fecha_sel = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_sel = None

    if not fecha_sel:
        ultimo_dia = VentaDiaria.query.filter(
            VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
        ).order_by(VentaDiaria.fecha.desc()).first()
        if ultimo_dia:
            fecha_sel = ultimo_dia.fecha
        else:
            fecha_sel = date.today()

    venta_dia = VentaDiaria.query.filter_by(fecha=fecha_sel).first()

    movimientos = MovimientoInventario.query.filter(
        MovimientoInventario.fecha == fecha_sel,
        MovimientoInventario.producto_id != None
    ).all()
    movimientos.sort(key=lambda x: x.producto.nombre if x.producto else '')

    dias_disponibles = VentaDiaria.query.filter(
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha.desc()).limit(15).all()

    return render_template('reportes/movimientos_inventario.html',
                           movimientos=movimientos,
                           fecha_sel=fecha_sel,
                           venta_dia=venta_dia,
                           dias_disponibles=dias_disponibles)


@bp.route('/movimientos-inventario')
@login_required
def movimientos_inventario():
    """Consulta de movimientos de inventario por día."""
    from app.models import MovimientoInventario
    fecha_str = request.args.get('fecha')
    fecha_sel = None

    if fecha_str:
        try:
            from datetime import datetime
            fecha_sel = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_sel = None

    if not fecha_sel:
        ultimo_dia = VentaDiaria.query.filter(
            VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
        ).order_by(VentaDiaria.fecha.desc()).first()
        if ultimo_dia:
            fecha_sel = ultimo_dia.fecha
        else:
            fecha_sel = date.today()

    venta_dia = VentaDiaria.query.filter_by(fecha=fecha_sel).first()

    movimientos = MovimientoInventario.query.filter(
        MovimientoInventario.fecha == fecha_sel,
        MovimientoInventario.producto_id != None
    ).all()
    movimientos.sort(key=lambda x: x.producto.nombre if x.producto else '')

    dias_disponibles = VentaDiaria.query.filter(
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha.desc()).limit(15).all()

    return render_template('reportes/movimientos_inventario.html',
                           movimientos=movimientos,
                           fecha_sel=fecha_sel,
                           venta_dia=venta_dia,
                           dias_disponibles=dias_disponibles)


@bp.route('/cortesias')
@login_required
def cortesias_reporte():
    """Informe de cortesías acumulado por producto."""
    from datetime import datetime

    fecha_desde = request.args.get('desde')
    fecha_hasta = request.args.get('hasta')

    query = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        VentaDetalle.es_cortesia == True
    )
    if fecha_desde:
        query = query.filter(VentaDiaria.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d').date())
    if fecha_hasta:
        query = query.filter(VentaDiaria.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d').date())

    detalles = query.all()

    # Agrupar por producto
    from collections import defaultdict
    resumen = defaultdict(lambda: {'cantidad': 0, 'valor_unitario': 0})

    for d in detalles:
        prod_nombre = d.producto.nombre
        resumen[prod_nombre]['cantidad'] += d.cantidad
        resumen[prod_nombre]['valor_unitario'] = float(d.precio_unitario)

    # Ordenar por cantidad descendente
    resumen_ordenado = dict(sorted(resumen.items(), key=lambda x: x[1]['cantidad'], reverse=True))
    total_cortesias = sum(v['cantidad'] for v in resumen.values())

    return render_template('reportes/cortesias.html',
                           resumen=resumen_ordenado,
                           total_cortesias=total_cortesias,
                           fecha_desde=fecha_desde or '',
                           fecha_hasta=fecha_hasta or '')


@bp.route('/acumulados')
@login_required
def acumulados():
    """Informe acumulado con promedio diario y gráfica de ventas por día."""
    from app.models import VentaDetalle, Producto, Categoria
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json

    # Filtro de mes (por defecto mes actual)
    mes = request.args.get('mes', date.today().month, type=int)
    anio = request.args.get('anio', date.today().year, type=int)

    # Ventas del mes
    ventas_mes = VentaDiaria.query.filter(
        db.extract('month', VentaDiaria.fecha) == mes,
        db.extract('year', VentaDiaria.fecha) == anio,
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha).all()

    # Datos para la gráfica (ventas por día)
    grafica_labels = [v.fecha.strftime('%d/%m') for v in ventas_mes]
    grafica_valores = [float(v.total_ventas) for v in ventas_mes]

    # Promedios
    total_acumulado = sum(float(v.total_ventas) for v in ventas_mes)
    dias_cerrados = len(ventas_mes)
    promedio_sin_hoy = 0
    promedio_con_hoy = 0

    if dias_cerrados > 1:
        promedio_sin_hoy = sum(float(v.total_ventas) for v in ventas_mes[:-1]) / (dias_cerrados - 1)
    if dias_cerrados > 0:
        promedio_con_hoy = total_acumulado / dias_cerrados

    # Ventas acumuladas por categoría y producto
    detalles_mes = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        db.extract('month', VentaDiaria.fecha) == mes,
        db.extract('year', VentaDiaria.fecha) == anio,
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo']),
        VentaDetalle.es_cortesia == False
    ).all()

    resumen_cat = defaultdict(lambda: {'productos': defaultdict(lambda: {'cantidad': 0, 'valor': 0}), 'total_cantidad': 0, 'total_valor': 0})

    for d in detalles_mes:
        cat_nombre = d.producto.categoria.nombre
        prod_nombre = d.producto.nombre
        resumen_cat[cat_nombre]['productos'][prod_nombre]['cantidad'] += d.cantidad
        resumen_cat[cat_nombre]['productos'][prod_nombre]['valor'] += float(d.subtotal)
        resumen_cat[cat_nombre]['total_cantidad'] += d.cantidad
        resumen_cat[cat_nombre]['total_valor'] += float(d.subtotal)

    return render_template('reportes/acumulados.html',
                           mes=mes,
                           anio=anio,
                           ventas_mes=ventas_mes,
                           total_acumulado=total_acumulado,
                           dias_cerrados=dias_cerrados,
                           promedio_sin_hoy=promedio_sin_hoy,
                           promedio_con_hoy=promedio_con_hoy,
                           resumen_cat=dict(resumen_cat),
                           grafica_labels=json.dumps(grafica_labels),
                           grafica_valores=json.dumps(grafica_valores))


@bp.route('/cantidades-promedio')
@login_required
def cantidades_promedio():
    """Informe de cantidades promedio por categoría y día."""
    from app.models import VentaDetalle, Categoria
    from collections import defaultdict
    import json

    mes = request.args.get('mes', date.today().month, type=int)
    anio = request.args.get('anio', date.today().year, type=int)

    # Días cerrados del mes
    ventas_mes = VentaDiaria.query.filter(
        db.extract('month', VentaDiaria.fecha) == mes,
        db.extract('year', VentaDiaria.fecha) == anio,
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha).all()

    dias_cerrados = len(ventas_mes)

    # Categorías visibles en ventas
    categorias = Categoria.query.filter_by(activa=True, visible_ventas=True).order_by(Categoria.nombre).all()

    # Cantidades por día por categoría
    cantidades_dia = defaultdict(lambda: defaultdict(int))  # {fecha: {cat_nombre: cantidad}}
    totales_cat = defaultdict(int)  # {cat_nombre: total_acumulado}

    for venta in ventas_mes:
        detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta.id, es_cortesia=False).all()
        for d in detalles:
            cat_nombre = d.producto.categoria.nombre
            cantidades_dia[venta.fecha.strftime('%d/%m')][cat_nombre] += d.cantidad
            totales_cat[cat_nombre] += d.cantidad

    # Promedios
    promedios = {}
    for cat in categorias:
        total = totales_cat.get(cat.nombre, 0)
        promedios[cat.nombre] = round(total / dias_cerrados, 1) if dias_cerrados > 0 else 0

    # Datos para gráfica: cantidades por día para cada categoría
    grafica_labels = [v.fecha.strftime('%d/%m') for v in ventas_mes]
    grafica_datasets = []
    colores = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336', '#00BCD4', '#795548']

    for i, cat in enumerate(categorias):
        if totales_cat.get(cat.nombre, 0) > 0:
            datos = [cantidades_dia[fecha][cat.nombre] for fecha in grafica_labels]
            grafica_datasets.append({
                'label': cat.nombre,
                'data': datos,
                'backgroundColor': colores[i % len(colores)] + '99',
                'borderColor': colores[i % len(colores)],
                'borderWidth': 1
            })

    # Total platos (almuerzos + parrillas + desayunos)
    categorias_platos = ['Almuerzos', 'Parrillas', 'Desayunos']
    total_platos = sum(totales_cat.get(c, 0) for c in categorias_platos)
    promedio_platos = round(total_platos / dias_cerrados, 1) if dias_cerrados > 0 else 0
    platos_almuerzos = totales_cat.get('Almuerzos', 0)
    platos_parrillas = totales_cat.get('Parrillas', 0)
    platos_desayunos = totales_cat.get('Desayunos', 0)

    # Valor total del mes y promedio en valor
    total_valor_mes = sum(float(v.total_ventas) for v in ventas_mes)
    promedio_valor = round(total_valor_mes / dias_cerrados, 0) if dias_cerrados > 0 else 0

    # Valores por categoría y por día
    valores_cat = defaultdict(float)
    valores_dia = defaultdict(lambda: defaultdict(float))
    for venta in ventas_mes:
        detalles_v = VentaDetalle.query.filter_by(venta_diaria_id=venta.id, es_cortesia=False).all()
        for d in detalles_v:
            cat_n = d.producto.categoria.nombre
            valores_cat[cat_n] += float(d.subtotal)
            valores_dia[venta.fecha.strftime('%d/%m')][cat_n] += float(d.subtotal)

    valor_platos = sum(valores_cat.get(c, 0) for c in categorias_platos)
    promedio_valor_platos = round(valor_platos / dias_cerrados, 0) if dias_cerrados > 0 else 0

    # Gráfica de valores por día (barras verticales agrupadas)
    grafica_val_labels = [v.fecha.strftime('%d/%m') for v in ventas_mes]
    grafica_val_datasets = [
        {'label': 'Total Día', 'data': [float(v.total_ventas) for v in ventas_mes], 'backgroundColor': '#212529'},
        {'label': 'Alm+Parr+Des', 'data': [valores_dia[f].get('Almuerzos',0)+valores_dia[f].get('Parrillas',0)+valores_dia[f].get('Desayunos',0) for f in grafica_val_labels], 'backgroundColor': '#0d6efd'},
        {'label': 'Almuerzos', 'data': [valores_dia[f].get('Almuerzos',0) for f in grafica_val_labels], 'backgroundColor': '#198754'},
        {'label': 'Parrillas', 'data': [valores_dia[f].get('Parrillas',0) for f in grafica_val_labels], 'backgroundColor': '#fd7e14'},
        {'label': 'Desayunos', 'data': [valores_dia[f].get('Desayunos',0) for f in grafica_val_labels], 'backgroundColor': '#6f42c1'},
    ]
    otras_cats = [c for c in valores_cat.keys() if c not in categorias_platos]
    if otras_cats:
        grafica_val_datasets.append({'label': 'Otros', 'data': [sum(valores_dia[f].get(c,0) for c in otras_cats) for f in grafica_val_labels], 'backgroundColor': '#6c757d'})

    return render_template('reportes/cantidades_promedio.html',
                           mes=mes, anio=anio, dias_cerrados=dias_cerrados,
                           totales_cat=dict(totales_cat), promedios=promedios,
                           grafica_labels=json.dumps(grafica_labels),
                           grafica_datasets=json.dumps(grafica_datasets),
                           total_platos=total_platos, promedio_platos=promedio_platos,
                           platos_almuerzos=platos_almuerzos, platos_parrillas=platos_parrillas,
                           platos_desayunos=platos_desayunos,
                           total_valor_mes=total_valor_mes, promedio_valor=promedio_valor,
                           valor_platos=valor_platos, promedio_valor_platos=promedio_valor_platos,
                           valores_cat=dict(valores_cat),
                           grafica_val_labels=json.dumps(grafica_val_labels),
                           grafica_val_datasets=json.dumps(grafica_val_datasets))
