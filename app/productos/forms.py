from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, BooleanField, SubmitField, IntegerField, FieldList, FormField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CategoriaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    descripcion = StringField('Descripción', validators=[Length(max=200)])
    activa = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


class ProductoForm(FlaskForm):
    nombre = StringField('Nombre del producto', validators=[DataRequired(), Length(max=150)])
    precio = DecimalField('Precio', validators=[DataRequired(), NumberRange(min=0)], places=2)
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    controla_inventario_directo = BooleanField('Controla inventario directo (1 a 1)')
    insumo_directo_id = SelectField('Insumo asociado', coerce=int, validators=[Optional()])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')


class ProductoInsumoForm(FlaskForm):
    """Formulario para asignar insumos que descuenta un producto."""
    insumo_id = SelectField('Insumo', coerce=int, validators=[DataRequired()])
    cantidad = DecimalField('Cantidad a descontar', validators=[DataRequired(), NumberRange(min=0.001)], places=3)
    submit = SubmitField('Agregar')
