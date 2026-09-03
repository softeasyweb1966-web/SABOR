from flask import render_template, request
from flask_login import login_required
from app import db
from app.reportes import bp
from app.models import VentaDiaria, MovimientoInventario, VentaDetalle, Compra, Gasto
from datetime import date
from decimal import Decimal


@bp.route('/')
@login_required
def index():
    return render_template('reportes/index.html')


@bp.route('/mensual')
@login_required
def informe_mensual():
    """P&G mensual, punto de equilibrio y comportamiento diario."""
    from calendar import monthrange
    from collections import defaultdict
    from datetime import timedelta
    import json
    import unicodedata

    mes = request.args.get('mes', date.today().month, type=int)
    anio = request.args.get('anio', date.today().year, type=int)
    utilidad_objetivo = Decimal(str(request.args.get('utilidad_objetivo', 0, type=float) or 0))
    dias_trabajo_param = request.args.get('dias_trabajo', type=int)
    if not 1 <= mes <= 12:
        mes = date.today().month
    if utilidad_objetivo < 0 or utilidad_objetivo >= 100:
        utilidad_objetivo = Decimal('0')

    inicio_mes = date(anio, mes, 1)
    ultimo_dia = monthrange(anio, mes)[1]
    fin_mes = date(anio, mes, ultimo_dia)

    ventas_dias = VentaDiaria.query.filter(
        VentaDiaria.fecha.between(inicio_mes, fin_mes),
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).order_by(VentaDiaria.fecha).all()
    compras = Compra.query.filter(Compra.fecha.between(inicio_mes, fin_mes)).all()
    gastos = Gasto.query.filter(Gasto.fecha.between(inicio_mes, fin_mes)).all()

    total_ventas = sum((venta.total_ventas for venta in ventas_dias), Decimal('0'))
    total_compras = sum((compra.costo_total for compra in compras), Decimal('0'))
    nomina = Decimal('0')
    servicios = Decimal('0')
    otros_gastos = Decimal('0')
    gastos_por_tipo = defaultdict(lambda: Decimal('0'))

    for gasto in gastos:
        nombre_tipo = gasto.tipo_gasto.nombre
        tipo_normalizado = unicodedata.normalize('NFKD', nombre_tipo).encode('ascii', 'ignore').decode().lower()
        gastos_por_tipo[nombre_tipo] += gasto.monto
        if 'nomina' in tipo_normalizado:
            nomina += gasto.monto
        elif 'servicio' in tipo_normalizado:
            servicios += gasto.monto
        else:
            otros_gastos += gasto.monto

    costos_fijos = nomina + servicios + otros_gastos
    margen_contribucion = total_ventas - total_compras
    margen_contribucion_pct = (margen_contribucion / total_ventas * 100) if total_ventas else Decimal('0')
    utilidad_neta = margen_contribucion - costos_fijos
    margen_neto_pct = (utilidad_neta / total_ventas * 100) if total_ventas else Decimal('0')

    # Las compras crecen junto con las ventas, usando el porcentaje real de compra del mes.
    porcentaje_compras = total_compras / total_ventas if total_ventas else Decimal('0')
    margen_bruto_pct = Decimal('1') - porcentaje_compras
    margen_disponible_pct = margen_bruto_pct - utilidad_objetivo / 100
    costos_totales = total_compras + costos_fijos
    ventas_objetivo = None
    compras_proyectadas = None
    incremento_compras = None
    utilidad_objetivo_valor = None
    diferencia_objetivo = None
    cobertura_objetivo_pct = None
    if total_ventas and margen_disponible_pct > 0:
        ventas_objetivo = costos_fijos / margen_disponible_pct
        compras_proyectadas = ventas_objetivo * porcentaje_compras
        incremento_compras = compras_proyectadas - total_compras
        utilidad_objetivo_valor = ventas_objetivo * utilidad_objetivo / 100
        diferencia_objetivo = total_ventas - ventas_objetivo
        cobertura_objetivo_pct = total_ventas / ventas_objetivo * 100

    categorias_platos = {'almuerzos': 'Almuerzos', 'desayunos': 'Desayunos', 'parrillas': 'Parrillas'}
    platos_por_categoria = {nombre: 0 for nombre in categorias_platos.values()}
    detalles_platos = db.session.query(VentaDetalle).join(VentaDiaria).filter(
        VentaDiaria.fecha.between(inicio_mes, fin_mes),
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo']),
        VentaDetalle.es_cortesia == False
    ).all()
    for detalle in detalles_platos:
        categoria = detalle.producto.categoria.nombre.strip().lower()
        if categoria in categorias_platos:
            platos_por_categoria[categorias_platos[categoria]] += detalle.cantidad

    total_platos = sum(platos_por_categoria.values())
    promedio_venta_por_plato = total_ventas / total_platos if total_platos else Decimal('0')
    platos_objetivo = ventas_objetivo / promedio_venta_por_plato if ventas_objetivo and promedio_venta_por_plato else Decimal('0')
    resumen_platos = []
    for categoria, cantidad in platos_por_categoria.items():
        proporcion = Decimal(cantidad) / total_platos if total_platos else Decimal('0')
        resumen_platos.append({
            'categoria': categoria,
            'cantidad': cantidad,
            'objetivo': platos_objetivo * proporcion
        })

    # El comportamiento diario permite ver si el ritmo de ventas acompana las compras y gastos.
    ventas_por_fecha = defaultdict(lambda: Decimal('0'))
    compras_por_fecha = defaultdict(lambda: Decimal('0'))
    gastos_por_fecha = defaultdict(lambda: Decimal('0'))
    for venta in ventas_dias:
        ventas_por_fecha[venta.fecha] += venta.total_ventas
    for compra in compras:
        compras_por_fecha[compra.fecha] += compra.costo_total
    for gasto in gastos:
        gastos_por_fecha[gasto.fecha] += gasto.monto

    fechas = [inicio_mes + timedelta(days=dia) for dia in range(ultimo_dia)]
    dias = [
        {
            'fecha': fecha,
            'ventas': ventas_por_fecha[fecha],
            'compras': compras_por_fecha[fecha],
            'gastos': gastos_por_fecha[fecha]
        }
        for fecha in fechas
    ]
    dias_con_ventas = [dia for dia in dias if dia['ventas'] > 0]
    mejor_dia = max(dias_con_ventas, key=lambda dia: dia['ventas']) if dias_con_ventas else None
    promedio_diario = total_ventas / len(dias_con_ventas) if dias_con_ventas else Decimal('0')
    dias_trabajo = dias_trabajo_param if dias_trabajo_param and dias_trabajo_param > 0 else len(dias_con_ventas)
    venta_diaria_objetivo = ventas_objetivo / dias_trabajo if ventas_objetivo and dias_trabajo else None
    diferencia_promedio_diario = promedio_diario - venta_diaria_objetivo if venta_diaria_objetivo else None

    if mes == 1:
        mes_anterior, anio_anterior = 12, anio - 1
    else:
        mes_anterior, anio_anterior = mes - 1, anio
    inicio_anterior = date(anio_anterior, mes_anterior, 1)
    fin_anterior = date(anio_anterior, mes_anterior, monthrange(anio_anterior, mes_anterior)[1])
    ventas_anterior = VentaDiaria.query.filter(
        VentaDiaria.fecha.between(inicio_anterior, fin_anterior),
        VentaDiaria.estado.in_(['cerrado_caja', 'cerrado_definitivo'])
    ).all()
    total_ventas_anterior = sum((venta.total_ventas for venta in ventas_anterior), Decimal('0'))
    variacion_ventas_pct = (
        (total_ventas - total_ventas_anterior) / total_ventas_anterior * 100
        if total_ventas_anterior else None
    )

    return render_template(
        'reportes/mensual.html',
        mes=mes,
        anio=anio,
        total_ventas=total_ventas,
        total_compras=total_compras,
        nomina=nomina,
        servicios=servicios,
        otros_gastos=otros_gastos,
        gastos_por_tipo=dict(sorted(gastos_por_tipo.items())),
        costos_fijos=costos_fijos,
        costos_totales=costos_totales,
        porcentaje_compras=porcentaje_compras,
        margen_bruto_pct=margen_bruto_pct,
        margen_contribucion=margen_contribucion,
        margen_contribucion_pct=margen_contribucion_pct,
        utilidad_neta=utilidad_neta,
        margen_neto_pct=margen_neto_pct,
        utilidad_objetivo=utilidad_objetivo,
        utilidad_objetivo_valor=utilidad_objetivo_valor,
        ventas_objetivo=ventas_objetivo,
        compras_proyectadas=compras_proyectadas,
        incremento_compras=incremento_compras,
        diferencia_objetivo=diferencia_objetivo,
        cobertura_objetivo_pct=cobertura_objetivo_pct,
        total_platos=total_platos,
        promedio_venta_por_plato=promedio_venta_por_plato,
        resumen_platos=resumen_platos,
        dias_con_ventas=len(dias_con_ventas),
        dias_trabajo=dias_trabajo,
        promedio_diario=promedio_diario,
        venta_diaria_objetivo=venta_diaria_objetivo,
        diferencia_promedio_diario=diferencia_promedio_diario,
        mejor_dia=mejor_dia,
        total_ventas_anterior=total_ventas_anterior,
        variacion_ventas_pct=variacion_ventas_pct,
        grafica_labels=json.dumps([fecha.strftime('%d') for fecha in fechas]),
        grafica_ventas=json.dumps([float(dia['ventas']) for dia in dias]),
        grafica_compras=json.dumps([float(dia['compras']) for dia in dias]),
        grafica_gastos=json.dumps([float(dia['gastos']) for dia in dias])
    )


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

    # Proteínas descargadas por ventas (via receta)
    from app.models import Receta
    ventas_proteinas = defaultdict(float)
    for venta in ventas_mes:
        detalles_v2 = VentaDetalle.query.filter_by(venta_diaria_id=venta.id).all()
        for d in detalles_v2:
            # Descuento directo
            if d.producto.maneja_inventario and 'PROTEINA' in d.producto.nombre.upper():
                ventas_proteinas[d.producto.nombre] += float(d.cantidad)
            # Descuento por receta
            for r in d.producto.receta:
                if 'PROTEINA' in r.insumo.nombre.upper():
                    ventas_proteinas[r.insumo.nombre] += float(r.cantidad * d.cantidad)

    # Compras y gastos del mes
    from app.models import Compra, Gasto
    compras_mes = Compra.query.filter(
        db.extract('month', Compra.fecha) == mes,
        db.extract('year', Compra.fecha) == anio
    ).all()
    total_compras_mes = sum(float(c.costo_total) for c in compras_mes)

    # Compras por categoría
    compras_por_cat = defaultdict(float)
    compras_proteinas = defaultdict(lambda: {'cantidad': 0, 'valor': 0})
    for c in compras_mes:
        cat_nombre = c.categoria.nombre if c.categoria else 'Sin categoría'
        compras_por_cat[cat_nombre] += float(c.costo_total)
        # Detalle proteínas
        if c.producto and 'PROTEINA' in c.producto.nombre.upper():
            compras_proteinas[c.producto.nombre]['cantidad'] += float(c.cantidad)
            compras_proteinas[c.producto.nombre]['valor'] += float(c.costo_total)

    gastos_mes = Gasto.query.filter(
        db.extract('month', Gasto.fecha) == mes,
        db.extract('year', Gasto.fecha) == anio
    ).all()
    total_gastos_mes = sum(float(g.monto) for g in gastos_mes)

    # Gastos por tipo
    gastos_por_tipo = defaultdict(float)
    for g in gastos_mes:
        gastos_por_tipo[g.tipo_gasto.nombre] += float(g.monto)

    total_egresos_mes = total_compras_mes + total_gastos_mes

    # Gráfica: TODAS las barras en VALORES, pero labels muestran cantidad excepto Total Día
    grafica_val_labels = [v.fecha.strftime('%d/%m') for v in ventas_mes]

    grafica_val_datasets = [
        {'label': 'Total Día', 'data': [float(v.total_ventas) for v in ventas_mes], 'backgroundColor': '#212529'},
        {'label': 'Alm+Parr+Des', 'data': [valores_dia[f].get('Almuerzos',0)+valores_dia[f].get('Parrillas',0)+valores_dia[f].get('Desayunos',0) for f in grafica_val_labels], 'backgroundColor': '#0d6efd',
         'cantidades': [cantidades_dia[f].get('Almuerzos',0)+cantidades_dia[f].get('Parrillas',0)+cantidades_dia[f].get('Desayunos',0) for f in grafica_val_labels]},
    ]
    if valores_cat.get('Almuerzos', 0) > 0:
        grafica_val_datasets.append({'label': 'Almuerzos', 'data': [valores_dia[f].get('Almuerzos',0) for f in grafica_val_labels], 'backgroundColor': '#198754',
            'cantidades': [cantidades_dia[f].get('Almuerzos',0) for f in grafica_val_labels]})
    if valores_cat.get('Parrillas', 0) > 0:
        grafica_val_datasets.append({'label': 'Parrillas', 'data': [valores_dia[f].get('Parrillas',0) for f in grafica_val_labels], 'backgroundColor': '#fd7e14',
            'cantidades': [cantidades_dia[f].get('Parrillas',0) for f in grafica_val_labels]})
    if valores_cat.get('Desayunos', 0) > 0:
        grafica_val_datasets.append({'label': 'Desayunos', 'data': [valores_dia[f].get('Desayunos',0) for f in grafica_val_labels], 'backgroundColor': '#6f42c1',
            'cantidades': [cantidades_dia[f].get('Desayunos',0) for f in grafica_val_labels]})
    otras_cats = [c for c in totales_cat.keys() if c not in categorias_platos and totales_cat[c] > 0]
    colores_otras = ['#6c757d', '#20c997', '#e83e8c', '#17a2b8', '#ffc107']
    for i, cat_o in enumerate(otras_cats):
        grafica_val_datasets.append({
            'label': cat_o,
            'data': [valores_dia[f].get(cat_o, 0) for f in grafica_val_labels],
            'backgroundColor': colores_otras[i % len(colores_otras)],
            'cantidades': [cantidades_dia[f].get(cat_o, 0) for f in grafica_val_labels]
        })

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
                           grafica_val_datasets=json.dumps(grafica_val_datasets),
                           total_egresos_mes=total_egresos_mes,
                           total_compras_mes=total_compras_mes,
                           total_gastos_mes=total_gastos_mes,
                           compras_por_cat=dict(compras_por_cat),
                           compras_proteinas=dict(compras_proteinas),
                           ventas_proteinas=dict(ventas_proteinas),
                           gastos_por_tipo=dict(gastos_por_tipo))
