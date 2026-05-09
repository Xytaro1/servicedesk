from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SelectField, StringField
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegisterForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(max=100)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=4)]
    )
    password_again = PasswordField(
        "Повторите пароль",
        validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class TicketForm(FlaskForm):
    title = StringField(
        "Название заявки",
        validators=[DataRequired(), Length(max=150)]
    )
    text = TextAreaField(
        "Описание проблемы",
        validators=[DataRequired()]
    )
    category = SelectField(
        "Категория",
        choices=[
            ("Компьютер", "Компьютер"),
            ("Интернет", "Интернет"),
            ("Принтер", "Принтер"),
            ("Аккаунт", "Аккаунт"),
            ("Другое", "Другое"),
        ],
        validators=[DataRequired()]
    )
    priority = SelectField(
        "Приоритет",
        choices=[
            ("Низкий", "Низкий"),
            ("Обычный", "Обычный"),
            ("Высокий", "Высокий"),
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Создать заявку")
