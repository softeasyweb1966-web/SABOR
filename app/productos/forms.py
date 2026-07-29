from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CategoriaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    descripcion = StringField('Descripción', validators=[Length(max=200)])
    visible_ventas = BooleanField('Visible en Ventas del Día', default=True)
    visible_compras = BooleanField('Visible en Compras', default=True)
    activa = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


class ProductoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=150)])
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
    ], validators=[DataRequired()])
    precio = DecimalField('Precio de venta ($)', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    se_vende = BooleanField('Se vende (aparece en ventas del día)', default=True)
    maneja_inventario = BooleanField('Maneja inventario (tiene stock)', default=False)
    unidad_medida = SelectField('Unidad de medida', choices=[
        ('unidades', 'Unidades'),
        ('kg', 'Kilogramos'),
        ('g', 'Gramos'),
        ('lb', 'Libras'),
        ('litros', 'Litros'),
        ('ml', 'Mililitros'),
        ('porciones', 'Porciones'),
    ], validators=[Optional()])
    stock_minimo = DecimalField('Stock mínimo', validators=[Optional(), NumberRange(min=0)], places=0, default=0)
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')


class RecetaForm(FlaskForm):
    """Formulario para asignar qué productos se descuentan al vender."""
    insumo_id = SelectField('Producto/Insumo a descontar', coerce=int, validators=[DataRequired()])
    cantidad = DecimalField('Cantidad a descontar', validators=[DataRequired(), NumberRange(min=0.001)], places=3)
    submit = SubmitField('Agregar')
