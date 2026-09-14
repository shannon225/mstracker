"""Local authenticated maintenance workflow. All mutations use CSRF and SQL parameters."""
import calendar
import hashlib
import secrets
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import SecurityError

from .db import audit, connect, uid
from .timeutils import iso, local_display, local_instant, utcnow, zone

bp = Blueprint("web", __name__)
DUMMY_HASH = generate_password_hash("not-a-real-account-password")


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@bp.before_app_request
def protect_request():
    g.user = None
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not submitted or not secrets.compare_digest(submitted, session.get("csrf", "")):
            abort(400, "Your form expired. Reload the page and try again.")
    if session.get("sid"):
        g.user = get_db().execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>? AND u.active=1",
            (token_hash(session["sid"]), iso(utcnow())),
        ).fetchone()
        if not g.user:
            session.clear()
    if request.endpoint not in ("web.login", "static") and request.endpoint and not g.user:
        return redirect(url_for("web.login"))


@bp.after_app_request
def response_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'none'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.app_context_processor
def template_context():
    return {"instrument": current_app.config["INSTRUMENT"], "csrf_token": csrf, "user": g.get("user"),
            "weekdays": list(calendar.day_name), "form": request.form}


@bp.app_template_filter("localtime")
def display_time(value):
    return local_display(value, current_app.config["INSTRUMENT"]["timezone"]).strftime("%b %d, %Y · %H:%M %Z")


@bp.app_errorhandler(400)
@bp.app_errorhandler(404)
@bp.app_errorhandler(413)
def page_error(error):
    if isinstance(error, SecurityError):
        # Host rejection happens before Flask creates a URL adapter.
        return "Invalid local host. Open http://127.0.0.1 with your configured port.", 400
    return render_template("error.html", message=error.description), error.code


@bp.app_errorhandler(sqlite3.OperationalError)
def database_error(error):
    return render_template("error.html", message="The database is unavailable or busy. Your change was not confirmed. Check the log before retrying."), 503


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("web.calendar_view"))
    error = None
    if request.method == "POST":
        db = get_db()
        username = request.form.get("username", "").strip().lower()[:80]
        now = utcnow()
        cutoff = iso(now - timedelta(minutes=5))
        with db:
            db.execute("DELETE FROM login_attempts WHERE window_start<?", (cutoff,))
            attempt = db.execute("SELECT * FROM login_attempts WHERE username=?", (username,)).fetchone()
            # Bound both individual account attempts and random-username bypasses.
            total = db.execute("SELECT coalesce(sum(failures),0) FROM login_attempts").fetchone()[0]
            if (attempt and attempt["failures"] >= 5) or total >= 30:
                return render_template("login.html", error="Too many attempts. Wait five minutes and try again."), 429
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            password = request.form.get("password", "")
            valid = len(password) <= 1024 and check_password_hash(user["password_hash"] if user else DUMMY_HASH, password)
            if user and user["active"] and valid:
                session.clear()
                session.permanent = True
                session["sid"] = secrets.token_urlsafe(32)
                db.execute("DELETE FROM login_attempts WHERE username=?", (username,))
                db.execute("DELETE FROM sessions WHERE expires_at<=?", (iso(now),))
                db.execute("INSERT INTO sessions VALUES (?,?,?)", (token_hash(session["sid"]), user["id"], iso(now + timedelta(hours=8))))
                audit(db, user["id"], "login", user["id"])
            else:
                db.execute("INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(username) DO UPDATE SET failures=failures+1", (username, iso(now)))
                error = "Unable to sign in. Check your username and password."
        if error is None:
            return redirect(url_for("web.calendar_view"))
    return render_template("login.html", error=error), 401 if error else 200


@bp.post("/logout")
def logout():
    db = get_db()
    with db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(session["sid"]),))
        audit(db, g.user["id"], "logout", g.user["id"])
    session.clear()
    return redirect(url_for("web.login"))


def text_field(name, limit, required=False):
    value = request.form.get(name, "").strip()
    if (required and not value) or len(value) > limit:
        raise ValueError(f"{name.replace('_', ' ').capitalize()} is required and must fit within {limit} characters." if required else f"{name.capitalize()} must fit within {limit} characters.")
    return value


def follow_up(instrument, after=None):
    value = request.form.get("follow_up", "")
    if not value:
        return None
    instant, _, _ = local_instant(value, instrument["timezone"], request.form.get("follow_up_fold", ""))
    if instant <= iso(utcnow()) or (after and instant <= after):
        raise ValueError("Follow-up must be later than now and the performed event.")
    return instant


def add_marker(db, task_id, due_at, event_id=None):
    settings = current_app.config["INSTRUMENT"]
    marker_id, now = uid(), iso(utcnow())
    db.execute("INSERT INTO calendar_markers (id,task_id,event_id,instrument_id,due_at,timezone,kind,created_at,updated_at) VALUES (?,?,?,?,?,?,'follow-up',?,?)",
               (marker_id, task_id, event_id, settings["instrument_id"], due_at, settings["timezone"], now, now))
    audit(db, g.user["id"], "follow_up_created", marker_id)


@bp.route("/tasks", methods=["GET", "POST"])
def tasks():
    db = get_db()
    settings = current_app.config["INSTRUMENT"]
    error = None
    if request.method == "POST":
        try:
            name, details = text_field("name", 120, True), text_field("details", 10000)
            category, recurrence = request.form.get("category"), request.form.get("recurrence")
            if category not in ("routine", "unplanned") or recurrence not in ("weekly", "one-time"):
                raise ValueError("Select a valid category and recurrence.")
            try:
                minutes = int(request.form.get("expected_minutes", ""))
                weekday = int(request.form.get("weekday", "")) if recurrence == "weekly" else None
            except ValueError:
                raise ValueError("Enter whole minutes and select a weekly day when needed.") from None
            if not 1 <= minutes <= 10080 or (weekday is not None and not 0 <= weekday <= 6):
                raise ValueError("Expected duration must be 1–10080 minutes; weekly day must be valid.")
            due = follow_up(settings)
            task_id, now = uid(), iso(utcnow())
            with db:
                db.execute("INSERT INTO tasks (id,instrument_id,name,details,category,expected_minutes,recurrence,weekday,follow_up_at,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (task_id, settings["instrument_id"], name, details, category, minutes, recurrence, weekday, due, g.user["id"], now, now))
                if due:
                    add_marker(db, task_id, due)
                audit(db, g.user["id"], "task_created", task_id)
            flash("Task created. You can now log maintenance for it.")
            return redirect(url_for("web.tasks"))
        except ValueError as exc:
            error = str(exc)
    rows = db.execute("SELECT * FROM tasks ORDER BY name COLLATE NOCASE,id").fetchall()
    return render_template("tasks.html", tasks=rows, error=error), 400 if error else 200


@bp.route("/events/new", methods=["GET", "POST"])
def new_event():
    db, error = get_db(), None
    settings = current_app.config["INSTRUMENT"]
    if request.method == "GET":
        # A signed token belongs to this form and user; multiple browser tabs work independently.
        from itsdangerous import URLSafeTimedSerializer
        submission = URLSafeTimedSerializer(current_app.secret_key, salt="event-form").dumps([g.user["id"], uid()])
    else:
        submission = request.form.get("submission", "")
        try:
            from itsdangerous import BadSignature, URLSafeTimedSerializer
            try:
                owner, key = URLSafeTimedSerializer(current_app.secret_key, salt="event-form").loads(submission, max_age=28800)
            except (BadSignature, ValueError, TypeError):
                raise ValueError("Event form expired. Open Log maintenance again.") from None
            if owner != g.user["id"]:
                raise ValueError("Event form belongs to another session. Open a new form.")
            existing = db.execute("SELECT id FROM events WHERE submission_key=?", (key,)).fetchone()
            if existing:
                return redirect(url_for("web.event_detail", event_id=existing["id"]))
            task = db.execute("SELECT * FROM tasks WHERE id=?", (request.form.get("task_id"),)).fetchone()
            if not task:
                raise ValueError("Choose an existing task.")
            occurred, original, fold = local_instant(request.form.get("occurred_at", ""), settings["timezone"], request.form.get("fold", ""))
            if occurred > iso(utcnow()):
                raise ValueError("Performed maintenance cannot be in the future.")
            status = request.form.get("completion_status") if task["category"] == "routine" else "unplanned"
            if status not in ("on-time", "early", "unplanned") or (task["category"] == "routine" and status == "unplanned"):
                raise ValueError("Choose on-time or early for routine maintenance.")
            notes = text_field("notes", 10000)
            due = follow_up(settings, occurred)
            event_id, now = uid(), iso(utcnow())
            with db:
                db.execute("INSERT INTO events (id,task_id,instrument_id,category,completion_status,occurred_at,original_local_time,original_timezone,original_fold,notes,performed_by,created_at,updated_at,submission_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (event_id, task["id"], settings["instrument_id"], task["category"], status, occurred, original, settings["timezone"], fold, notes, g.user["id"], now, now, key))
                if due:
                    add_marker(db, task["id"], due, event_id)
                audit(db, g.user["id"], "event_created", event_id)
            flash("Maintenance saved.")
            return redirect(url_for("web.event_detail", event_id=event_id))
        except ValueError as exc:
            error = str(exc)
    rows = db.execute("SELECT * FROM tasks ORDER BY name COLLATE NOCASE,id").fetchall()
    now_local = utcnow().astimezone(zone(settings["timezone"])).strftime("%Y-%m-%dT%H:%M")
    return render_template("new_event.html", tasks=rows, error=error, submission=submission, now_local=now_local), 400 if error else 200


EVENT_SELECT = "SELECT e.*,t.name AS task_name,u.username FROM events e JOIN tasks t ON t.id=e.task_id JOIN users u ON u.id=e.performed_by "


@bp.get("/events/<event_id>")
def event_detail(event_id):
    db = get_db()
    event = db.execute(EVENT_SELECT + "WHERE e.id=?", (event_id,)).fetchone()
    if not event:
        abort(404)
    markers = db.execute("SELECT * FROM calendar_markers WHERE event_id=? ORDER BY due_at,id", (event_id,)).fetchall()
    return render_template("event.html", event=event, markers=markers)


@bp.get("/log")
def maintenance_log():
    try:
        page = int(request.args.get("page", "1"))
        if not 1 <= page <= 1000000:
            raise ValueError
    except ValueError:
        abort(400, "Invalid page number.")
    rows = get_db().execute(EVENT_SELECT + "ORDER BY e.occurred_at DESC,e.id LIMIT 51 OFFSET ?", ((page - 1) * 50,)).fetchall()
    return render_template("log.html", events=rows[:50], page=page, more=len(rows) > 50)


@bp.get("/")
def calendar_view():
    tz = current_app.config["INSTRUMENT"]["timezone"]
    today = utcnow().astimezone(zone(tz)).date()
    try:
        month = datetime.strptime(request.args.get("month", today.strftime("%Y-%m")), "%Y-%m").date()
        if not 1900 <= month.year <= 2100:
            raise ValueError
    except ValueError:
        abort(400, "Choose a month between 1900 and 2100.")
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
    first, end = weeks[0][0], weeks[-1][-1] + timedelta(days=1)
    start_utc = iso(datetime.combine(first, datetime.min.time(), zone(tz)))
    end_utc = iso(datetime.combine(end, datetime.min.time(), zone(tz)))
    items = defaultdict(list)
    for row in get_db().execute(EVENT_SELECT + "WHERE e.occurred_at>=? AND e.occurred_at<? ORDER BY e.occurred_at,e.id", (start_utc, end_utc)):
        item = dict(row)
        item["when"] = local_display(row["occurred_at"], tz)
        item["href"] = url_for("web.event_detail", event_id=row["id"])
        items[item["when"].date()].append(item)
    for row in get_db().execute("SELECT m.*,t.name AS task_name FROM calendar_markers m JOIN tasks t ON t.id=m.task_id WHERE m.due_at>=? AND m.due_at<? ORDER BY m.due_at,m.id", (start_utc, end_utc)):
        item = dict(row)
        item.update(category="follow-up", when=local_display(row["due_at"], tz), href=url_for("web.event_detail", event_id=row["event_id"]) if row["event_id"] else url_for("web.tasks"))
        items[item["when"].date()].append(item)
    for values in items.values():
        values.sort(key=lambda item: (item["when"], item["id"]))
    previous = (month - timedelta(days=1)).strftime("%Y-%m") if month > date(1900, 1, 1) else None
    following = (month.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m") if month < date(2100, 12, 1) else None
    return render_template("calendar.html", month=month, weeks=weeks, items=items, today=today, previous=previous, following=following)
