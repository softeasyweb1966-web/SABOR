from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from datetime import date


class CreditoForm(FlaskForm):
    persona_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    monto_total = DecimalField('Monto del crédito ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    observacion = StringField('Observación', validators=[Length(max=200)])
    submit = SubmitField('Registrar Crédito')


class PagoCreditoForm(FlaskForm):
    monto = DecimalField('Monto del abono ($)', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    forma_pago_id = SelectField('Forma de pago', coerce=int, validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    observacion = StringField('Observación', validators=[Length(max=200)])
    submit = SubmitField('Registrar Abono')
