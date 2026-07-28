from flask_wtf import FlaskForm
from wtforms import IntegerField, DecimalField, BooleanField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from datetime import date


class VentaDetalleForm(FlaskForm):
    producto_id = IntegerField('Producto', validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Agregar')


class DescuentoAlmuerzosForm(FlaskForm):
    descuento = DecimalField('Descuento almuerzos ($)', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    submit = SubmitField('Aplicar Descuento')


class CierreCajaForm(FlaskForm):
    """Cierre parcial: cajero indica cómo se recibió el dinero."""
    total_efectivo = DecimalField('Efectivo', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    total_nequi = DecimalField('Nequi', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    total_daviplata = DecimalField('Daviplata', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    total_transferencia = DecimalField('Transferencia Cuenta', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    total_credito = DecimalField('Crédito', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    submit = SubmitField('Cerrar Caja')


class AbrirDiaForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Abrir Día')
