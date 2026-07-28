"""
Script de configuracion inicial del proyecto SABOR.
Ejecutar despues de configurar DATABASE_URL en el archivo .env

Uso:
    1. Edita .env y coloca tu password de PostgreSQL en DATABASE_URL
    2. Crea la base de datos 'sabor_db' manualmente si no existe:
       - Abre pgAdmin o psql
       - Ejecuta: CREATE DATABASE sabor_db;
    3. Ejecuta: python setup.py
"""
import os
import sys

# Asegurar encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app, db
from app.models import Usuario, Rol, Categoria, FormaPago, TipoGasto

app = create_app()

with app.app_context():
    try:
        # Crear todas las tablas
        db.create_all()
        print("[OK] Tablas creadas correctamente.")

        # Crear roles
        roles = ['Administrador', 'Cajero', 'Mesero']
        for nombre_rol in roles:
            if not Rol.query.filter_by(nombre=nombre_rol).first():
                db.session.add(Rol(nombre=nombre_rol, descripcion=f'Rol de {nombre_rol.lower()}'))
        db.session.commit()
        print("[OK] Roles creados: Administrador, Cajero, Mesero")

        # Crear categorias
        categorias = ['Desayunos', 'Almuerzos', 'Parrillas', 'Porciones y Otros', 'Bebidas']
        for nombre_cat in categorias:
            if not Categoria.query.filter_by(nombre=nombre_cat).first():
                db.session.add(Categoria(nombre=nombre_cat))
        db.session.commit()
        print("[OK] Categorias creadas: " + ", ".join(categorias))

        # Crear formas de pago
        formas = ['Efectivo', 'Nequi', 'Transferencia', 'Credito']
        for nombre_fp in formas:
            if not FormaPago.query.filter_by(nombre=nombre_fp).first():
                db.session.add(FormaPago(nombre=nombre_fp))
        db.session.commit()
        print("[OK] Formas de pago: " + ", ".join(formas))

        # Crear tipos de gasto
        tipos_gasto = ['Nomina', 'Servicios', 'Otros']
        for nombre_tg in tipos_gasto:
            if not TipoGasto.query.filter_by(nombre=nombre_tg).first():
                db.session.add(TipoGasto(nombre=nombre_tg))
        db.session.commit()
        print("[OK] Tipos de gasto: " + ", ".join(tipos_gasto))

        # Crear usuario administrador
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
            print("[OK] Usuario administrador creado.")
        else:
            print("[OK] Usuario admin ya existe.")

        print("")
        print("=" * 50)
        print("  CONFIGURACION COMPLETADA")
        print("=" * 50)
        print("")
        print("  Usuario: admin")
        print("  Password: admin123")
        print("")
        print("  Para iniciar el servidor:")
        print("  python run.py")
        print("")
        print("  Luego abre: http://localhost:5000")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        print("")
        print("Verifica que:")
        print("1. PostgreSQL este corriendo")
        print("2. La base de datos 'sabor_db' exista")
        print("3. DATABASE_URL en .env tenga la password correcta")
        sys.exit(1)
