from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class TerceroForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired(), Length(max=150)])
    telefono = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    tipo = SelectField('Tipo', choices=[
        ('ambos', 'Cortesía y Crédito'),
        ('cortesia', 'Solo Cortesía'),
        ('credito', 'Solo Crédito'),
    ], validators=[DataRequired()])
    observacion = StringField('Observación', validators=[Length(max=200)])
    activa = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')
