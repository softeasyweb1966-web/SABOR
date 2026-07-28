from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import Usuario


class UsuarioForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    nombre_completo = StringField('Nombre completo', validators=[DataRequired(), Length(max=150)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    rol_id = SelectField('Rol', coerce=int, validators=[DataRequired()])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

    def validate_username(self, username):
        user = Usuario.query.filter_by(username=username.data).first()
        if user and (not hasattr(self, '_usuario_id') or user.id != self._usuario_id):
            raise ValidationError('Este nombre de usuario ya existe.')

    def validate_email(self, email):
        user = Usuario.query.filter_by(email=email.data).first()
        if user and (not hasattr(self, '_usuario_id') or user.id != self._usuario_id):
            raise ValidationError('Este email ya está registrado.')


class UsuarioEditForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    nombre_completo = StringField('Nombre completo', validators=[DataRequired(), Length(max=150)])
    password = PasswordField('Nueva contraseña (dejar vacío para no cambiar)')
    rol_id = SelectField('Rol', coerce=int, validators=[DataRequired()])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Actualizar')
