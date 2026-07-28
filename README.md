# SABOR - Sistema de Gestión de Restaurante

## Requisitos
- Python 3.11+
- PostgreSQL 16

## Instalación rápida

### 1. Ambiente virtual (ya creado)
```bash
python -m venv venv
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Configurar base de datos
Edita el archivo `.env` y coloca la contraseña correcta de PostgreSQL:
```
DATABASE_URL=postgresql://postgres:TU_PASSWORD@localhost:5432/sabor_db
```

### 3. Crear la base de datos
Desde pgAdmin o psql:
```sql
CREATE DATABASE sabor_db;
```

### 4. Inicializar tablas y datos
```bash
python setup.py
```

### 5. Ejecutar
```bash
python run.py
```
Abrir en el navegador: http://localhost:5000

### Credenciales por defecto
- **Usuario:** admin
- **Contraseña:** admin123

## Estructura del Proyecto
```
SABOR/
├── app/
│   ├── auth/          # Login/Logout
│   ├── usuarios/      # CRUD de usuarios con roles
│   ├── productos/     # Categorías y productos
│   ├── inventario/    # Insumos y compras
│   ├── ventas/        # Registro diario de ventas
│   ├── cortesias/     # Control de cortesías
│   ├── creditos/      # Créditos y abonos
│   ├── gastos/        # Gastos administrativos
│   ├── reportes/      # Informes
│   ├── templates/     # Vistas HTML
│   └── models.py      # Modelos de BD
├── config.py
├── run.py
├── setup.py
└── requirements.txt
```

## Roles del sistema
- **Administrador**: Acceso total incluyendo gestión de usuarios
- **Cajero**: Ventas, créditos, cierres
- **Mesero**: Registro de ventas
