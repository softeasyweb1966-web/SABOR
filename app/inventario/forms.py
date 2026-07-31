from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date


class CompraItemForm(FlaskForm):
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    producto_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    cantidad = DecimalField('Cantidad', validators=[DataRequired(), NumberRange(min=0.001)], places=3)
    costo_total = DecimalField('Costo total ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    submit = SubmitField('Agregar Item')


class ComprobanteForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    proveedor = StringField('Proveedor', validators=[Optional(), Length(max=150)])
    forma_pago = SelectField('Forma de pago', choices=[
        ('Caja General', 'Caja General'),
        ('Caja Menor', 'Caja Menor'),
    ], validators=[DataRequired()])
    observacion = StringField('Observación', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Finalizar Comprobante')
