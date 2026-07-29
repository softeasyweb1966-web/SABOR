"""
Migración: Unificar Productos e Insumos en una sola tabla.
- Agrega nuevas columnas a la tabla productos
- Migra datos de insumos a productos (los que no existan ya)
- Crea tabla recetas
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        # 1. Agregar nuevas columnas a productos
        columnas_producto = [
            ("tipo", "VARCHAR(20) DEFAULT 'producto'"),
            ("se_vende", "BOOLEAN DEFAULT TRUE"),
            ("maneja_inventario", "BOOLEAN DEFAULT FALSE"),
            ("unidad_medida", "VARCHAR(50) DEFAULT 'unidades'"),
            ("stock_actual", "NUMERIC(12,3) DEFAULT 0"),
            ("stock_minimo", "NUMERIC(12,3) DEFAULT 0"),
        ]
        for col, tipo in columnas_producto:
            try:
                conn.execute(text(f"ALTER TABLE productos ADD COLUMN {col} {tipo}"))
                conn.commit()
                print(f"OK columna productos: {col}")
            except:
                conn.rollback()
                print(f"Ya existe: productos.{col}")

        # 2. Crear tabla recetas
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recetas (
                    id SERIAL PRIMARY KEY,
                    producto_id INTEGER NOT NULL REFERENCES productos(id),
                    insumo_id INTEGER NOT NULL REFERENCES productos(id),
                    cantidad NUMERIC(12,3) NOT NULL
                )
            """))
            conn.commit()
            print("OK tabla recetas creada")
        except:
            conn.rollback()
            print("Tabla recetas ya existe")

        # 3. Agregar producto_id a compras (para apuntar a productos en vez de insumos)
        try:
            conn.execute(text("ALTER TABLE compras ADD COLUMN producto_id INTEGER REFERENCES productos(id)"))
            conn.commit()
            print("OK columna compras.producto_id")
        except:
            conn.rollback()
            print("Ya existe: compras.producto_id")

        # 4. Agregar producto_id a movimientos_inventario
        try:
            conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN producto_id INTEGER REFERENCES productos(id)"))
            conn.commit()
            print("OK columna movimientos_inventario.producto_id")
        except:
            conn.rollback()
            print("Ya existe: movimientos_inventario.producto_id")

    # 5. Actualizar productos existentes
    from app.models import Producto, Categoria
    
    # Productos con controla_inventario_directo -> maneja_inventario=True
    productos_directos = db.session.execute(
        text("SELECT id, controla_inventario_directo FROM productos WHERE controla_inventario_directo = TRUE")
    ).fetchall()
    for p in productos_directos:
        db.session.execute(
            text("UPDATE productos SET maneja_inventario = TRUE, unidad_medida = 'unidades' WHERE id = :id"),
            {"id": p[0]}
        )
    db.session.commit()
    print(f"Actualizados {len(productos_directos)} productos con inventario directo -> maneja_inventario=TRUE")

    # Todos los productos existentes se venden (ya estaban en ventas)
    db.session.execute(text("UPDATE productos SET se_vende = TRUE WHERE se_vende IS NULL"))
    db.session.execute(text("UPDATE productos SET tipo = 'producto' WHERE tipo IS NULL"))
    db.session.commit()
    print("Todos los productos marcados como se_vende=TRUE, tipo=producto")

    # 6. Migrar insumos que NO tienen producto equivalente
    insumos = db.session.execute(text("""
        SELECT i.id, i.nombre, i.unidad_medida, i.stock_actual, i.stock_minimo, i.categoria_id
        FROM insumos i 
        WHERE i.activo = TRUE 
        AND NOT EXISTS (
            SELECT 1 FROM productos p WHERE UPPER(p.nombre) = UPPER(i.nombre)
        )
    """)).fetchall()
    
    for ins in insumos:
        cat_id = ins[5]
        if not cat_id:
            # Buscar categoria "Otros" o la primera disponible
            cat = Categoria.query.filter_by(nombre='Otros').first()
            cat_id = cat.id if cat else 1
        
        db.session.execute(text("""
            INSERT INTO productos (nombre, categoria_id, tipo, precio, se_vende, maneja_inventario, 
                                   unidad_medida, stock_actual, stock_minimo, activo)
            VALUES (:nombre, :cat_id, 'producto', 0, FALSE, TRUE, :unidad, :stock, :stock_min, TRUE)
        """), {
            "nombre": ins[1],
            "cat_id": cat_id,
            "unidad": ins[2],
            "stock": ins[3],
            "stock_min": ins[4]
        })
    db.session.commit()
    print(f"Migrados {len(insumos)} insumos como productos (se_vende=FALSE, maneja_inventario=TRUE)")

    # 7. Migrar recetas de producto_insumo a recetas (producto -> producto)
    recetas_old = db.session.execute(text("""
        SELECT pi.producto_id, i.nombre, pi.cantidad
        FROM producto_insumo pi
        JOIN insumos i ON pi.insumo_id = i.id
    """)).fetchall()
    
    migradas = 0
    for r in recetas_old:
        # Buscar el producto que corresponde al insumo
        prod_insumo = db.session.execute(
            text("SELECT id FROM productos WHERE UPPER(nombre) = UPPER(:nombre) AND maneja_inventario = TRUE LIMIT 1"),
            {"nombre": r[1]}
        ).fetchone()
        if prod_insumo:
            # Verificar que no exista ya
            existe = db.session.execute(
                text("SELECT 1 FROM recetas WHERE producto_id = :pid AND insumo_id = :iid"),
                {"pid": r[0], "iid": prod_insumo[0]}
            ).fetchone()
            if not existe:
                db.session.execute(
                    text("INSERT INTO recetas (producto_id, insumo_id, cantidad) VALUES (:pid, :iid, :cant)"),
                    {"pid": r[0], "iid": prod_insumo[0], "cant": r[2]}
                )
                migradas += 1
    db.session.commit()
    print(f"Migradas {migradas} recetas a la nueva tabla")

    print("\n=== MIGRACIÓN COMPLETADA ===")
    print("Resumen de productos:")
    resumen = db.session.execute(text("""
        SELECT tipo, se_vende, maneja_inventario, COUNT(*) 
        FROM productos 
        WHERE activo = TRUE
        GROUP BY tipo, se_vende, maneja_inventario
        ORDER BY tipo, se_vende DESC, maneja_inventario DESC
    """)).fetchall()
    for r in resumen:
        print(f"  Tipo={r[0]}, Se vende={r[1]}, Maneja inv={r[2]}: {r[3]} productos")
