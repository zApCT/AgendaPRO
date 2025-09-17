from datetime import datetime, date, timedelta
import os
from dateutil.relativedelta import relativedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "agendapro.db")

# --------- DB RESOLVER ---------
def resolve_db_uri():
    url = os.getenv("DATABASE_URL")
    if url:
        # Render/Heroku usano "postgres://", SQLAlchemy vuole "postgresql+psycopg://"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url
    # fallback: SQLite in locale
    return f"sqlite:///{DB_PATH}"

# --------- APP CONFIG ---------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = resolve_db_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- MODELS ----------
class Client(db.Model):
    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", back_populates="client", cascade="all, delete-orphan")

class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)
    client = db.relationship("Client", back_populates="appointments")

# ---------- HELPERS ----------
def week_range(target_date: date):
    monday = target_date - timedelta(days=target_date.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    return monday, days

def parse_dt(date_str, time_str):
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def seed_demo():
    if Client.query.count() > 0:
        return
    c1 = Client(name="Mario Rossi", email="mario@example.com", phone="+39 333 111 2222", notes="Cliente storico")
    c2 = Client(name="Studio Bianchi", email="info@studiobianchi.it", phone="+39 02 123456", notes="Fatturazione mensile")
    c3 = Client(name="Dottoressa Verdi", email="verdi@med.it", phone="+39 06 987654", notes="Richiede promemoria")
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
    ap1 = Appointment(title="Consulenza iniziale", start_at=now, end_at=now + timedelta(hours=1), client=c1, location="Ufficio")
    ap2 = Appointment(title="Revisione mensile", start_at=now + timedelta(days=1, hours=2), end_at=now + timedelta(days=1, hours=3), client=c2, location="Online")
    ap3 = Appointment(title="Follow-up", start_at=now + timedelta(days=2, hours=1), end_at=now + timedelta(days=2, hours=2), client=c3, location="Studio")
    db.session.add_all([ap1, ap2, ap3])
    db.session.commit()

# ---------- ROUTES ----------
@app.route("/")
def dashboard():
    today = date.today()
    monday, days = week_range(today)
    start_week = datetime.combine(monday, datetime.min.time())
    end_week = start_week + timedelta(days=7)

    todays_appts = Appointment.query.filter(
        Appointment.start_at >= datetime.combine(today, datetime.min.time()),
        Appointment.start_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).order_by(Appointment.start_at).all()

    week_appts = Appointment.query.filter(
        Appointment.start_at >= start_week,
        Appointment.start_at < end_week
    ).all()

    active_clients = db.session.query(Client).join(Appointment, isouter=True)\
        .filter((Appointment.start_at >= today - relativedelta(months=3)) | (Appointment.id.is_(None)))\
        .count()

    recent_clients = Client.query.order_by(Client.created_at.desc()).limit(5).all()

    return render_template("dashboard.html",
                           todays_appts=todays_appts,
                           week_count=len(week_appts),
                           clients_count=Client.query.count(),
                           active_clients=active_clients,
                           recent_clients=recent_clients)

@app.route("/calendar")
def calendar():
    qdate = request.args.get("date")
    if qdate:
        try:
            base = datetime.strptime(qdate, "%Y-%m-%d").date()
        except ValueError:
            base = date.today()
    else:
        base = date.today()

    monday, days = week_range(base)
    start_week = datetime.combine(monday, datetime.min.time())
    end_week = start_week + timedelta(days=7)

    appts = Appointment.query.filter(
        Appointment.start_at >= start_week,
        Appointment.start_at < end_week
    ).order_by(Appointment.start_at).all()

    grouped = {d: [] for d in days}
    for ap in appts:
        grouped[ap.start_at.date()].append(ap)

    prev_week = (monday - timedelta(days=7)).strftime("%Y-%m-%d")
    next_week = (monday + timedelta(days=7)).strftime("%Y-%m-%d")

    return render_template("calendar.html", days=days, grouped=grouped, monday=monday,
                           prev_week=prev_week, next_week=next_week)

# ---- Clients ----
@app.route("/clients")
def clients_list():
    q = request.args.get("q","").strip()
    query = Client.query
    if q:
        like = f"%{q}%"
        query = query.filter((Client.name.ilike(like)) | (Client.email.ilike(like)) | (Client.phone.ilike(like)))
    clients = query.order_by(Client.created_at.desc()).all()
    return render_template("clients.html", clients=clients, q=q)

@app.route("/clients/new", methods=["GET", "POST"])
def clients_new():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if not name:
            flash("Il nome è obbligatorio.","error")
            return redirect(url_for("clients_new"))
        client = Client(
            name=name,
            email=request.form.get("email","").strip() or None,
            phone=request.form.get("phone","").strip() or None,
            notes=request.form.get("notes","").strip() or None
        )
        db.session.add(client)
        db.session.commit()
        flash("Cliente creato.","success")
        return redirect(url_for("clients_list"))
    return render_template("client_form.html", client=None)

@app.route("/clients/<int:client_id>")
def clients_detail(client_id):
    client = Client.query.get_or_404(client_id)
    appts = Appointment.query.filter_by(client_id=client.id).order_by(Appointment.start_at.desc()).all()
    return render_template("client_detail.html", client=client, appts=appts)

@app.route("/clients/<int:client_id>/edit", methods=["GET","POST"])
def clients_edit(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == "POST":
        client.name = request.form.get("name","").strip() or client.name
        client.email = request.form.get("email","").strip() or None
        client.phone = request.form.get("phone","").strip() or None
        client.notes = request.form.get("notes","").strip() or None
        db.session.commit()
        flash("Cliente aggiornato.","success")
        return redirect(url_for("clients_detail", client_id=client.id))
    return render_template("client_form.html", client=client)

@app.route("/clients/<int:client_id>/delete", methods=["POST"])
def clients_delete(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash("Cliente eliminato.","success")
    return redirect(url_for("clients_list"))

# ---- Appointments ----
@app.route("/appointments/new", methods=["GET","POST"])
def appt_new():
    clients = Client.query.order_by(Client.name.asc()).all()
    if request.method == "POST":
        title = request.form.get("title","").strip()
        date_str = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        client_id = request.form.get("client_id") or None
        location = request.form.get("location","").strip() or None
        notes = request.form.get("notes","").strip() or None

        if not title or not date_str or not start_time or not end_time:
            flash("Compila titolo, data, orari.","error")
            return redirect(url_for("appt_new"))

        start_at = parse_dt(date_str, start_time)
        end_at = parse_dt(date_str, end_time)
        if end_at <= start_at:
            flash("L'orario di fine deve essere successivo all'inizio.","error")
            return redirect(url_for("appt_new"))

        ap = Appointment(title=title, start_at=start_at, end_at=end_at,
                         client_id=int(client_id) if client_id else None,
                         location=location, notes=notes)
        db.session.add(ap)
        db.session.commit()
        flash("Appuntamento creato.","success")
        return redirect(url_for("calendar"))
    return render_template("appointment_form.html", clients=clients, appt=None)

@app.route("/appointments/<int:appt_id>/edit", methods=["GET","POST"])
def appt_edit(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    clients = Client.query.order_by(Client.name.asc()).all()
    if request.method == "POST":
        appt.title = request.form.get("title","").strip() or appt.title
        date_str = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        appt.client_id = int(request.form.get("client_id")) if request.form.get("client_id") else None
        appt.location = request.form.get("location","").strip() or None
        appt.notes = request.form.get("notes","").strip() or None

        if date_str and start_time and end_time:
            appt.start_at = parse_dt(date_str, start_time)
            appt.end_at = parse_dt(date_str, end_time)
            if appt.end_at <= appt.start_at:
                flash("L'orario di fine deve essere successivo all'inizio.","error")
                return redirect(url_for("appt_edit", appt_id=appt.id))

        db.session.commit()
        flash("Appuntamento aggiornato.","success")
        return redirect(url_for("calendar"))
    return render_template("appointment_form.html", clients=clients, appt=appt)

@app.route("/appointments/<int:appt_id>/delete", methods=["POST"])
def appt_delete(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    flash("Appuntamento eliminato.","success")
    return redirect(url_for("calendar"))

# ---------- APP START ----------
with app.app_context():
    db.create_all()
    if os.environ.get("SEED_DEMO"):
        seed_demo()

if __name__ == "__main__":
    app.run(debug=True)
