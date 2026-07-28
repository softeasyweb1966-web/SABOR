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
# CATEGORÍAS Y PRODUCTOS
# ============================================================

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    activa = db.Column(db.Boolean, default=True)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

    def __repr__(self):
        return f'<Categoria {self.nombre}>'


class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    controla_inventario_directo = db.Column(db.Boolean, default=False)
    insumo_directo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    # Relación con insumos que descuenta (receta)
    descuentos_inventario = db.relationship('ProductoInsumo', backref='producto', lazy=True)
    # Insumo directo (1 a 1, ej: Coca-Cola)
    insumo_directo = db.relationship('Insumo', backref='productos_directos', foreign_keys=[insumo_directo_id])

    def __repr__(self):
        return f'<Producto {self.nombre}>'


# ============================================================
# INVENTARIO E INSUMOS
# ============================================================

class Insumo(db.Model):
    __tablename__ = 'insumos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    unidad_medida = db.Column(db.String(50), nullable=False)  # kg, litros, unidades, etc.
    stock_actual = db.Column(db.Numeric(12, 3), default=0)
    stock_minimo = db.Column(db.Numeric(12, 3), default=0)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Insumo {self.nombre} ({self.stock_actual} {self.unidad_medida})>'


class MovimientoInventario(db.Model):
    """Foto diaria del movimiento de cada insumo. Se registra al cerrar caja."""
    __tablename__ = 'movimientos_inventario'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    saldo_inicio = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    compras = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    ventas = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    saldo_final = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    insumo = db.relationship('Insumo', backref='movimientos')

    __table_args__ = (db.UniqueConstraint('fecha', 'insumo_id', name='uq_mov_fecha_insumo'),)


class ProductoInsumo(db.Model):
    """Define qué insumos y cantidades se descuentan al vender un producto."""
    __tablename__ = 'producto_insumo'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)  # cantidad que se descuenta por unidad vendida
    insumo = db.relationship('Insumo', backref='productos_asociados')


class CategoriaCompra(db.Model):
    """Categorías para clasificar las compras."""
    __tablename__ = 'categorias_compra'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activa = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CategoriaCompra {self.nombre}>'


class Compra(db.Model):
    """Registro de compras de insumos para alimentar el inventario."""
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    categoria_compra_id = db.Column(db.Integer, db.ForeignKey('categorias_compra.id'), nullable=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
    costo_total = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    proveedor = db.Column(db.String(150))
    observacion = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    categoria_compra = db.relationship('CategoriaCompra', backref='compras')
    insumo = db.relationship('Insumo', backref='compras')
    usuario = db.relationship('Usuario', backref='compras_registradas')


# ============================================================
# FORMAS DE PAGO
# ============================================================

class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # Efectivo, Nequi, Crédito
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
    # Estados: abierto, cerrado_caja, cerrado_definitivo
    estado = db.Column(db.String(30), default='abierto')
    cerrada = db.Column(db.Boolean, default=False)  # mantener por compatibilidad
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    cerrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario = db.relationship('Usuario', backref='ventas_registradas', foreign_keys=[usuario_id])
    cerrado_por = db.relationship('Usuario', backref='cierres_validados', foreign_keys=[cerrado_por_id])
    detalles = db.relationship('VentaDetalle', backref='venta_diaria', lazy=True)
    pagos_electronicos = db.relationship('PagoElectronico', backref='venta_diaria', lazy=True)

    def __repr__(self):
        return f'<VentaDiaria {self.fecha}>'


class PagoElectronico(db.Model):
    """Detalle individual de pagos electrónicos para cruzar con plataformas."""
    __tablename__ = 'pagos_electronicos'
    id = db.Column(db.Integer, primary_key=True)
    venta_diaria_id = db.Column(db.Integer, db.ForeignKey('ventas_diarias.id'), nullable=False)
    plataforma = db.Column(db.String(30), nullable=False)  # Nequi, Daviplata, Cuenta
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    referencia = db.Column(db.String(100))  # Número de transacción o referencia
    titular = db.Column(db.String(100))  # Nombre de quien paga (opcional)
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
# CORTESÍAS Y PERSONAS
# ============================================================

class Persona(db.Model):
    """Terceros: personas para cortesías, créditos o ambos."""
    __tablename__ = 'personas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20))
    observacion = db.Column(db.String(200))
    tipo = db.Column(db.String(20), default='ambos')  # cortesia, credito, ambos
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
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, abonado, cancelado
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
    nombre = db.Column(db.String(100), unique=True, nullable=False)  # Nómina, Servicios, Otros
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<TipoGasto {self.nombre}>'


class Gasto(db.Model):
    __tablename__ = 'gastos'
    id = db.Column(db.Integer, primary_key=True)
    tipo_gasto_id = db.Column(db.Integer, db.ForeignKey('tipos_gasto.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    descripcion = db.Column(db.String(200), nullable=False)
    detalle = db.Column(db.String(200))  # Empleado, referencia servicio, etc.
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago = db.Column(db.String(30), default='Efectivo')  # Efectivo, Nequi, Daviplata, Cuenta
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo_gasto = db.relationship('TipoGasto', backref='gastos')
    usuario = db.relationship('Usuario', backref='gastos_registrados')
