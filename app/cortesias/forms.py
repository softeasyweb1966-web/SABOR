from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, DateField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date


class PersonaForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired(), Length(max=150)])
    telefono = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    observacion = StringField('Observación', validators=[Length(max=200)])
    activa = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


class CortesiaForm(FlaskForm):
    persona_id = SelectField('Persona', coerce=int, validators=[DataRequired()])
    producto_id = SelectField('Producto (almuerzo)', coerce=int, validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)], default=1)
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    observacion = StringField('Observación', validators=[Length(max=200)])
    submit = SubmitField('Registrar Cortesía')
