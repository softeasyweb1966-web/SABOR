from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, BooleanField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date


class CompraForm(FlaskForm):
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    producto_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    cantidad = DecimalField('Cantidad', validators=[DataRequired(), NumberRange(min=0.001)], places=3)
    costo_total = DecimalField('Costo total ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    proveedor = StringField('Proveedor', validators=[Optional(), Length(max=150)])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    observacion = StringField('Observación', validators=[Length(max=200)])
    submit = SubmitField('Registrar Compra')
