"""
Migracion: guardar la fecha real de registro de compras.

Agrega fecha_registro a comprobantes_compra y compras. Para datos existentes,
usa la fecha de compra como valor inicial a las 00:00:00.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        columnas = [
            ("comprobantes_compra", "fecha_registro"),
            ("compras", "fecha_registro"),
        ]

        for tabla, columna in columnas:
            try:
                conn.execute(text(
                    f"ALTER TABLE {tabla} ADD COLUMN {columna} TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ))
                conn.commit()
                print(f"OK columna {tabla}.{columna}")
            except Exception:
                conn.rollback()
                print(f"Ya existe: {tabla}.{columna}")

            conn.execute(text(
                f"UPDATE {tabla} SET {columna} = fecha WHERE {columna} IS NULL"
            ))
            conn.commit()

    print("Migracion completada.")
