from app import create_app, db
from app.models import Usuario, Rol, Categoria, FormaPago, TipoGasto

app = create_app()


@app.cli.command('init-db')
def init_db():
    """Inicializa la base de datos con datos básicos."""
    db.create_all()

    # Crear roles si no existen
    roles = ['Administrador', 'Cajero', 'Mesero']
    for nombre_rol in roles:
        if not Rol.query.filter_by(nombre=nombre_rol).first():
            db.session.add(Rol(nombre=nombre_rol, descripcion=f'Rol de {nombre_rol.lower()}'))

    # Crear categorías por defecto
    categorias = ['Desayunos', 'Almuerzos', 'Parrillas', 'Porciones y Otros', 'Bebidas']
    for nombre_cat in categorias:
        if not Categoria.query.filter_by(nombre=nombre_cat).first():
            db.session.add(Categoria(nombre=nombre_cat))

    # Crear formas de pago
    formas = ['Efectivo', 'Nequi', 'Transferencia', 'Crédito']
    for nombre_fp in formas:
        if not FormaPago.query.filter_by(nombre=nombre_fp).first():
            db.session.add(FormaPago(nombre=nombre_fp))

    # Crear tipos de gasto
    tipos_gasto = ['Nómina', 'Servicios', 'Otros']
    for nombre_tg in tipos_gasto:
        if not TipoGasto.query.filter_by(nombre=nombre_tg).first():
            db.session.add(TipoGasto(nombre=nombre_tg))

    # Crear usuario administrador por defecto
    if not Usuario.query.filter_by(username='admin').first():
        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        admin = Usuario(
            username='admin',
            email='admin@sabor.com',
            nombre_completo='Administrador del Sistema',
            rol_id=rol_admin.id,
            activo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

    db.session.commit()
    print('✓ Base de datos inicializada correctamente.')
    print('  Usuario: admin | Contraseña: admin123')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
