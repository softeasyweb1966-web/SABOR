from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, BooleanField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date


class InsumoForm(FlaskForm):
    nombre = StringField('Nombre del insumo', validators=[DataRequired(), Length(max=150)])
    unidad_medida = SelectField('Unidad de medida', choices=[
        ('unidades', 'Unidades'),
        ('kg', 'Kilogramos'),
        ('g', 'Gramos'),
        ('lb', 'Libras'),
        ('litros', 'Litros'),
        ('ml', 'Mililitros'),
        ('porciones', 'Porciones'),
    ], validators=[DataRequired()])
    stock_minimo = DecimalField('Stock mínimo', validators=[Optional(), NumberRange(min=0)], places=3, default=0)
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')


class CategoriaCompraForm(FlaskForm):
    nombre = StringField('Nombre de categoría', validators=[DataRequired(), Length(max=100)])
    activa = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


class CompraForm(FlaskForm):
    categoria_compra_id = SelectField('Categoría de compra', coerce=int, validators=[DataRequired()])
    insumo_id = SelectField('Insumo (actualiza inventario)', coerce=int, validators=[DataRequired()])
    cantidad = DecimalField('Cantidad (en unidad del insumo)', validators=[DataRequired(), NumberRange(min=0.001)], places=3)
    costo_total = DecimalField('Costo total ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    proveedor = StringField('Proveedor', validators=[Optional(), Length(max=150)])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    observacion = StringField('Observación', validators=[Length(max=200)])
    submit = SubmitField('Registrar Compra')
