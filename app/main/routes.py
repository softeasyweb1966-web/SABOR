from flask import render_template
from flask_login import login_required
from app import db
from app.main import bp
from app.models import VentaDiaria, VentaDetalle, Categoria
from datetime import date
from decimal import Decimal


@bp.route('/')
@login_required
def index():
    hoy = date.today()
    venta_dia = VentaDiaria.query.filter_by(fecha=hoy).first()

    resumen_categorias = {}
    total_ventas = Decimal('0')

    if venta_dia:
        detalles = VentaDetalle.query.filter_by(venta_diaria_id=venta_dia.id).all()
        categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()

        for cat in categorias:
            cat_items = [d for d in detalles if d.producto.categoria_id == cat.id and not d.es_cortesia]
            cortesias = [d for d in detalles if d.producto.categoria_id == cat.id and d.es_cortesia]
            if cat_items or cortesias:
                resumen_categorias[cat.nombre] = {
                    'total_cantidad': sum(d.cantidad for d in cat_items),
                    'total_cortesias': sum(d.cantidad for d in cortesias),
                    'total_dinero': sum(d.subtotal for d in cat_items)
                }

        total_ventas = sum(d.subtotal for d in detalles if not d.es_cortesia)

    return render_template('main/index.html', venta_dia=venta_dia, resumen_categorias=resumen_categorias, total_ventas=total_ventas)
