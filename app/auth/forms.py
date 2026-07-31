from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')


class CambiarClaveForm(FlaskForm):
    clave_actual = PasswordField('Contraseña actual', validators=[DataRequired()])
    clave_nueva = PasswordField('Nueva contraseña', validators=[DataRequired(), Length(min=4)])
    clave_confirmar = PasswordField('Confirmar nueva contraseña', validators=[DataRequired(), EqualTo('clave_nueva', message='Las contraseñas no coinciden')])
    submit = SubmitField('Cambiar Contraseña')
