from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date


class TipoGastoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')


class GastoForm(FlaskForm):
    tipo_gasto_id = SelectField('Tipo de gasto', coerce=int, validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired(), Length(max=200)])
    detalle = StringField('Detalle (empleado, referencia, servicio)', validators=[Optional(), Length(max=200)])
    monto = DecimalField('Monto ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    forma_pago = SelectField('Forma de pago', choices=[
        ('Efectivo', 'Efectivo'),
        ('Nequi', 'Nequi'),
        ('Daviplata', 'Daviplata'),
        ('Cuenta', 'Transferencia/Cuenta'),
    ], validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Registrar Gasto')
