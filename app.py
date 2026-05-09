from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required
from flask_login import login_user, logout_user

from db import db
from forms import LoginForm, RegisterForm, TicketForm
from models import Ticket, User


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "servicedesk.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

app = Flask(__name__)
app.config["SECRET_KEY"] = "servicedesk_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Войдите в аккаунт, чтобы открыть страницу."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def index():
    return render_template("index.html", title="ServiceDesk")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("profile"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash("Пользователь с таким email уже есть.")
            return render_template(
                "register.html",
                title="Регистрация",
                form=form
            )

        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(
            "Регистрация прошла успешно. Теперь можно войти."
        )
        return redirect(url_for("login"))

    return render_template("register.html", title="Регистрация", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("profile"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("profile"))

        flash("Неверный email или пароль.")

    return render_template("login.html", title="Вход", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    tickets_count = Ticket.query.filter_by(user_id=current_user.id).count()
    return render_template(
        "profile.html",
        title="Личный кабинет",
        tickets_count=tickets_count
    )


@app.route("/tickets")
@login_required
def tickets():
    user_tickets = Ticket.query.filter_by(
        user_id=current_user.id
    ).order_by(Ticket.created_date.desc()).all()
    return render_template(
        "tickets.html",
        title="Мои заявки",
        tickets=user_tickets
    )


@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        ticket = Ticket(
            title=form.title.data,
            text=form.text.data,
            category=form.category.data,
            priority=form.priority.data,
            status="Новая",
            user_id=current_user.id
        )
        db.session.add(ticket)
        db.session.commit()
        flash("Заявка создана.")
        return redirect(url_for("tickets"))

    return render_template(
        "ticket_form.html",
        title="Новая заявка",
        form=form
    )


@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket or ticket.user_id != current_user.id:
        abort(404)

    return render_template(
        "ticket_detail.html",
        title=ticket.title,
        ticket=ticket
    )


def create_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    create_db()
    app.run(host="127.0.0.1", port=8080, debug=True)
