from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required
from flask_login import login_user, logout_user
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename

from db import db
from forms import DeleteForm, LoginForm, RegisterForm, StatusForm, TicketForm
from models import Ticket, User


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "servicedesk.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt"}

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


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def allowed_file(name):
    if "." not in name:
        return False

    extension = name.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def save_ticket_file(file, ticket):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        return None

    name = secure_filename(file.filename)
    name = f"ticket_{ticket.id}_{name}"
    file.save(app.config["UPLOAD_FOLDER"] / name)
    return name


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

        is_first_user = User.query.count() == 0
        user = User(
            name=form.name.data,
            email=form.email.data,
            is_admin=is_first_user
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Регистрация прошла успешно. Теперь можно войти.")
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
    if current_user.is_admin:
        user_tickets = Ticket.query.order_by(Ticket.created_date.desc()).all()
        title = "Все заявки"
    else:
        user_tickets = Ticket.query.filter_by(
            user_id=current_user.id
        ).order_by(Ticket.created_date.desc()).all()
        title = "Мои заявки"

    return render_template("tickets.html", title=title, tickets=user_tickets)


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

        file = form.file.data
        name = save_ticket_file(file, ticket)
        if file and file.filename and not name:
            db.session.delete(ticket)
            db.session.commit()
            flash("Можно загрузить только png, jpg, jpeg, pdf или txt.")
            return render_template(
                "ticket_form.html",
                title="Новая заявка",
                form=form
            )

        if name:
            ticket.file_name = name
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
    if not ticket:
        abort(404)

    if not current_user.is_admin and ticket.user_id != current_user.id:
        abort(404)

    return render_template(
        "ticket_detail.html",
        title=ticket.title,
        ticket=ticket,
        form=StatusForm(status=ticket.status),
        delete_form=DeleteForm()
    )


@app.route("/admin")
@login_required
@admin_required
def admin():
    tickets = Ticket.query.order_by(Ticket.created_date.desc()).all()
    forms = {}
    for ticket in tickets:
        forms[ticket.id] = StatusForm(status=ticket.status)

    return render_template(
        "admin.html",
        title="Админ-панель",
        tickets=tickets,
        forms=forms,
        delete_form=DeleteForm()
    )


@app.route("/admin/tickets/<int:ticket_id>/status", methods=["POST"])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        abort(404)

    form = StatusForm()
    if form.validate_on_submit():
        ticket.status = form.status.data
        db.session.commit()
        flash("Статус заявки обновлен.")

    return redirect(url_for("admin"))


@app.route("/admin/tickets/<int:ticket_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        abort(404)

    form = DeleteForm()
    if form.validate_on_submit():
        if ticket.file_name:
            file = app.config["UPLOAD_FOLDER"] / ticket.file_name
            if file.exists():
                file.unlink()

        db.session.delete(ticket)
        db.session.commit()
        flash("Заявка удалена.")

    return redirect(url_for("admin"))


def update_old_db():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "user" in tables:
        columns = [column["name"] for column in inspector.get_columns("user")]
        if "is_admin" not in columns:
            db.session.execute(
                text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            )
            db.session.commit()

        admin = User.query.filter_by(is_admin=True).first()
        first_user = User.query.order_by(User.id).first()
        if first_user and not admin:
            first_user.is_admin = True
            db.session.commit()

    if "ticket" in tables:
        columns = [
            column["name"] for column in inspector.get_columns("ticket")
        ]
        if "file_name" not in columns:
            db.session.execute(
                text("ALTER TABLE ticket ADD COLUMN file_name VARCHAR(200)")
            )
            db.session.commit()


def create_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()
        update_old_db()


if __name__ == "__main__":
    create_db()
    app.run(host="127.0.0.1", port=8080, debug=True)
