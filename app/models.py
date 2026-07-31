from datetime import datetime, date
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# ============================================================
# USUARIOS Y ROLES
# ============================================================

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# ============================================================
# CATEGORÍAS (única tabla para ventas y compras)
# ============================================================

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    activa = db.Column(db.Boolean, default=True)
    visible_ventas = db.Column(db.Boolean, default=True)
    visible_compras = db.Column(db.Boolean, default=True)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

    def __repr__(self):
        return f'<Categoria {self.nombre}>'


# ============================================================
# PRODUCTOS (unificado: productos, insumos, servicios)
# ============================================================

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    tipo = db.Column(db.String(20), default='producto')  # producto, servicio
    precio = db.Column(db.Numeric(12, 2), default=0)  # precio de venta (0 si no se vende)
    se_vende = db.Column(db.Boolean, default=True)  # aparece en ventas del día
    maneja_inventario = db.Column(db.Boolean, default=False)  # tiene stock que se mueve
    unidad_medida = db.Column(db.String(50), default='unidades')
    stock_actual = db.Column(db.Numeric(12, 3), default=0)
    stock_minimo = db.Column(db.Numeric(12, 3), default=0)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    # Receta: qué productos descuenta al venderse
    receta = db.relationship('Receta', backref='producto', lazy=True,
                             foreign_keys='Receta.producto_id')

    def __repr__(self):
        return f'<Producto {self.nombre}>'


class Receta(db.Model):
    """Define qué productos/insumos se descuentan al vender un producto."""
    __tablename__ = 'recetas'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    insumo = db.relationship('Producto', foreign_keys=[insumo_id], backref='usado_en_recetas')


# ============================================================
# COMPRAS
# ============================================================

class Compra(db.Model):
    """Registro de compras."""
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    comprobante_id = db.Column(db.Integer, db.ForeignKey('comprobantes_compra.id'), nullable=True)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    costo_total = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    proveedor = db.Column(db.String(150))
    observacion = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    producto = db.relationship('Producto', backref='compras')
    categoria = db.relationship('Categoria', backref='compras')
    comprobante = db.relationship('ComprobanteCompra', backref='items')
    usuario = db.relationship('Usuario', backref='compras_registradas')


class ComprobanteCompra(db.Model):
    """Encabezado de comprobante de compra (agrupa varios items)."""
    __tablename__ = 'comprobantes_compra'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    proveedor = db.Column(db.String(150))
    forma_pago = db.Column(db.String(20), default='Caja General')  # Caja Menor, Caja General
    total = db.Column(db.Numeric(12, 2), default=0)
    observacion = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    usuario = db.relationship('Usuario', backref='comprobantes_compra')

    def __repr__(self):
        return f'<ComprobanteCompra {self.id} {self.fecha}>'


# ============================================================
# CAJA MENOR
# ============================================================

class CajaMenor(db.Model):
    """Configuración y saldo de la caja menor."""
    __tablename__ = 'caja_menor'
    id = db.Column(db.Integer, primary_key=True)
    saldo_actual = db.Column(db.Numeric(12, 2), default=0)
    tope = db.Column(db.Numeric(12, 2), default=0)
    movimientos = db.relationship('MovimientoCajaMenor', backref='caja_menor', lazy=True)

    def __repr__(self):
        return f'<CajaMenor saldo={self.saldo_actual}>'


class MovimientoCajaMenor(db.Model):
    """Movimientos de caja menor (abastecimiento y compras)."""
    __tablename__ = 'movimientos_caja_menor'
    id = db.Column(db.Integer, primary_key=True)
    caja_menor_id = db.Column(db.Integer, db.ForeignKey('caja_menor.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    tipo = db.Column(db.String(20), nullable=False)  # abastecimiento, compra
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    descripcion = db.Column(db.String(200))
    comprobante_id = db.Column(db.Integer, db.ForeignKey('comprobantes_compra.id'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    comprobante = db.relationship('ComprobanteCompra', backref='movimiento_caja_menor')
    usuario = db.relationship('Usuario', backref='movimientos_caja_menor')


class AjusteInventario(db.Model):
    """Ajustes de inventario: carga inicial, conteo físico, merma/desperdicio."""
    __tablename__ = 'ajustes_inventario'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # carga_inicial, ajuste_conteo, merma
    cantidad_anterior = db.Column(db.Numeric(12, 3), nullable=False)
    cantidad_nueva = db.Column(db.Numeric(12, 3), nullable=False)
    diferencia = db.Column(db.Numeric(12, 3), nullable=False)
    valor = db.Column(db.Numeric(12, 2), default=0)  # valor de la cantidad ajustada
    motivo = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    producto = db.relationship('Producto', backref='ajustes')
    usuario = db.relationship('Usuario', backref='ajustes_inventario')


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

class MovimientoInventario(db.Model):
    """Foto diaria del movimiento de cada producto con inventario."""
    __tablename__ = 'movimientos_inventario'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    saldo_inicio = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    compras = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    ventas = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    saldo_final = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    producto = db.relationship('Producto', backref='movimientos')

    __table_args__ = (db.UniqueConstraint('fecha', 'producto_id', name='uq_mov_fecha_producto'),)


# ============================================================
# FORMAS DE PAGO
# ============================================================

class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    activa = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<FormaPago {self.nombre}>'


# ============================================================
# VENTAS
# ============================================================

class VentaDiaria(db.Model):
    """Encabezado del registro diario de ventas."""
    __tablename__ = 'ventas_diarias'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False, default=date.today)
    total_ventas = db.Column(db.Numeric(12, 2), default=0)
    total_efectivo = db.Column(db.Numeric(12, 2), default=0)
    total_nequi = db.Column(db.Numeric(12, 2), default=0)
    total_daviplata = db.Column(db.Numeric(12, 2), default=0)
    total_transferencia = db.Column(db.Numeric(12, 2), default=0)
    total_credito = db.Column(db.Numeric(12, 2), default=0)
    descuento_almuerzos = db.Column(db.Numeric(12, 2), default=0)
    justificacion_descuento = db.Column(db.String(200))
    estado = db.Column(db.String(30), default='abierto')
    cerrada = db.Column(db.Boolean, default=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    cerrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario = db.relationship('Usuario', backref='ventas_registradas', foreign_keys=[usuario_id])
    cerrado_por = db.relationship('Usuario', backref='cierres_validados', foreign_keys=[cerrado_por_id])
    detalles = db.relationship('VentaDetalle', backref='venta_diaria', lazy=True)
    pagos_electronicos = db.relationship('PagoElectronico', backref='venta_diaria', lazy=True)

    def __repr__(self):
        return f'<VentaDiaria {self.fecha}>'


class PagoElectronico(db.Model):
    """Detalle individual de pagos electrónicos."""
    __tablename__ = 'pagos_electronicos'
    id = db.Column(db.Integer, primary_key=True)
    venta_diaria_id = db.Column(db.Integer, db.ForeignKey('ventas_diarias.id'), nullable=False)
    plataforma = db.Column(db.String(30), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    referencia = db.Column(db.String(100))
    titular = db.Column(db.String(100))
    observacion = db.Column(db.String(200))

    def __repr__(self):
        return f'<PagoElectronico {self.plataforma} ${self.monto}>'


class VentaDetalle(db.Model):
    """Detalle de cada item vendido en el día."""
    __tablename__ = 'ventas_detalle'
    id = db.Column(db.Integer, primary_key=True)
    venta_diaria_id = db.Column(db.Integer, db.ForeignKey('ventas_diarias.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    descuento = db.Column(db.Numeric(12, 2), default=0)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'))
    es_credito = db.Column(db.Boolean, default=False)
    es_cortesia = db.Column(db.Boolean, default=False)
    cliente_credito_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=True)
    producto = db.relationship('Producto', backref='ventas')
    forma_pago = db.relationship('FormaPago', backref='ventas')
    cliente_credito = db.relationship('Persona', backref='compras_credito', foreign_keys=[cliente_credito_id])


# ============================================================
# TERCEROS (cortesías y créditos)
# ============================================================

class Persona(db.Model):
    """Terceros: personas para cortesías, créditos o ambos."""
    __tablename__ = 'personas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20))
    observacion = db.Column(db.String(200))
    tipo = db.Column(db.String(20), default='ambos')
    activa = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Persona {self.nombre}>'


class Cortesia(db.Model):
    """Registro de cortesías entregadas."""
    __tablename__ = 'cortesias'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today)
    persona_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    observacion = db.Column(db.String(200))
    persona = db.relationship('Persona', backref='cortesias')
    producto = db.relationship('Producto', backref='cortesias')


# ============================================================
# CRÉDITOS
# ============================================================

class Credito(db.Model):
    """Control de créditos otorgados."""
    __tablename__ = 'creditos'
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('personas.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    monto_total = db.Column(db.Numeric(12, 2), nullable=False)
    saldo_pendiente = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')
    venta_detalle_id = db.Column(db.Integer, db.ForeignKey('ventas_detalle.id'), nullable=True)
    observacion = db.Column(db.String(200))
    persona = db.relationship('Persona', backref='creditos')
    venta_detalle = db.relationship('VentaDetalle', backref='credito')
    pagos = db.relationship('PagoCredito', backref='credito', lazy=True)


class PagoCredito(db.Model):
    """Registro de abonos/pagos a créditos."""
    __tablename__ = 'pagos_credito'
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('creditos.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'))
    observacion = db.Column(db.String(200))
    forma_pago = db.relationship('FormaPago', backref='pagos_credito')


# ============================================================
# GASTOS ADMINISTRATIVOS
# ============================================================

class TipoGasto(db.Model):
    __tablename__ = 'tipos_gasto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<TipoGasto {self.nombre}>'


class Gasto(db.Model):
    __tablename__ = 'gastos'
    id = db.Column(db.Integer, primary_key=True)
    tipo_gasto_id = db.Column(db.Integer, db.ForeignKey('tipos_gasto.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    descripcion = db.Column(db.String(200), nullable=False)
    detalle = db.Column(db.String(200))
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago = db.Column(db.String(30), default='Efectivo')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo_gasto = db.relationship('TipoGasto', backref='gastos')
    usuario = db.relationship('Usuario', backref='gastos_registrados')


# ============================================================
# TABLAS LEGACY (mantener por compatibilidad con datos existentes)
# ============================================================

class CategoriaCompra(db.Model):
    __tablename__ = 'categorias_compra'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activa = db.Column(db.Boolean, default=True)


class Insumo(db.Model):
    """LEGACY - Se mantiene por datos existentes. Usar Producto en su lugar."""
    __tablename__ = 'insumos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    unidad_medida = db.Column(db.String(50), nullable=False)
    stock_actual = db.Column(db.Numeric(12, 3), default=0)
    stock_minimo = db.Column(db.Numeric(12, 3), default=0)
    categoria_compra_id = db.Column(db.Integer, db.ForeignKey('categorias_compra.id'), nullable=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True)


class ProductoInsumo(db.Model):
    """LEGACY - Se mantiene por datos existentes."""
    __tablename__ = 'producto_insumo'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
