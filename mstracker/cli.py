"""Local administration shared by source and self-contained distributions."""
import csv
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile

import click
from werkzeug.security import generate_password_hash

from . import __version__, create_app
from .db import audit, instance, migrate, opened, process_lock, uid
from .timeutils import iso, utcnow, zone


def default_data_dir():
    import sys
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path.home() / ".local/share"
    return root / "MSTracker"


def password_hash(password):
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must contain 12–1024 characters.")
    return generate_password_hash(password, method="scrypt")


def valid_username(username):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", username):
        raise ValueError("Username must be 1–80 letters, digits, dots, underscores or hyphens, starting with a letter/digit.")
    return username.lower()


def setup_instance(data_dir, name, model, timezone_name, weekday, username, password):
    zone(timezone_name)
    username, hashed = valid_username(username), password_hash(password)
    if not name.strip() or len(name) > 120 or not model.strip() or len(model) > 120:
        raise ValueError("Instrument name and model must contain 1–120 characters.")
    if not 0 <= weekday <= 6:
        raise ValueError("Weekday must be 0 (Monday) through 6 (Sunday).")
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    database = data_dir / "mstracker.sqlite3"
    with process_lock(data_dir):
        # Reserve the name atomically. Never overwrite a configured or failed setup.
        with database.open("xb"):
            pass
        database.chmod(0o600)
        with opened(database) as db:
            migrate(db)
            now, instance_id, instrument_id, user_id, task_id = iso(utcnow()), uid(), uid(), uid(), uid()
            with db:
                db.execute("INSERT INTO instance (singleton,id,instrument_id,name,model,timezone,created_at,updated_at,secret_key) VALUES (1,?,?,?,?,?,?,?,?)",
                           (instance_id, instrument_id, name.strip(), model.strip(), timezone_name, now, now, secrets.token_hex(32)))
                db.execute("INSERT INTO users (id,username,password_hash,created_at) VALUES (?,?,?,?)", (user_id, username, hashed, now))
                db.execute("INSERT INTO tasks (id,instrument_id,name,details,category,expected_minutes,recurrence,weekday,created_by,created_at,updated_at) VALUES (?,?,?,?,'routine',30,'weekly',?,?,?,?)",
                           (task_id, instrument_id, "Change ion transfer tube", "Example task: confirm the procedure and expected duration for your instrument.", weekday, user_id, now, now))
                audit(db, user_id, "instance_setup", instrument_id)


def change_user(database, username, action, password=None):
    username = valid_username(username)
    hashed = password_hash(password) if password is not None else None
    with opened(database) as db:
        with db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if action == "create":
                if user:
                    raise ValueError("Username already exists.")
                if hashed is None:
                    raise ValueError("A password is required.")
                user_id = uid()
                db.execute("INSERT INTO users (id,username,password_hash,created_at) VALUES (?,?,?,?)", (user_id, username, hashed, iso(utcnow())))
            else:
                if not user:
                    raise ValueError("Unknown username.")
                user_id = user["id"]
                if action == "reset":
                    if hashed is None:
                        raise ValueError("A password is required.")
                    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, user_id))
                elif action in ("disable", "enable"):
                    db.execute("UPDATE users SET active=? WHERE id=?", (int(action == "enable"), user_id))
                else:
                    raise ValueError("Unknown account action.")
                db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            db.execute("DELETE FROM login_attempts WHERE username=?", (username,))
            audit(db, None, "local_user_" + action, user_id)


def check_database(path):
    with opened(path) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Database integrity validation failed.")
        return dict(instance(db))


def backup_database(database, destination):
    destination = Path(destination)
    with destination.open("xb"):
        pass
    destination.chmod(0o600)
    try:
        with opened(database) as source, opened(destination) as target:
            source.backup(target)
        check_database(destination)
    except Exception:
        destination.unlink(missing_ok=True)  # Only this newly created, incomplete output.
        raise


def restore_database(database, source):
    database, source = Path(database), Path(source)
    if not source.is_file() or source.resolve() == database.resolve():
        raise ValueError("Choose an existing backup different from the live database.")
    with process_lock(database.parent):
        live = check_database(database)
        # Validate/migrate a disposable copy, never the supplied backup.
        fd, temp_name = tempfile.mkstemp(prefix="restore-", suffix=".sqlite3", dir=database.parent)
        os.close(fd)
        temp = Path(temp_name)
        try:
            with opened(source) as source_db, opened(temp) as target:
                source_db.backup(target)
                migrate(target)
                restored = dict(instance(target))
                if (restored["id"], restored["instrument_id"]) != (live["id"], live["instrument_id"]):
                    raise ValueError("Backup belongs to another instrument instance.")
                with target:
                    target.execute("DELETE FROM sessions")
                    target.execute("DELETE FROM login_attempts")
                    target.execute("UPDATE instance SET secret_key=?,updated_at=?,revision=revision+1 WHERE singleton=1", (secrets.token_hex(32), iso(utcnow())))
                    audit(target, None, "local_restore", live["instrument_id"])
            check_database(temp)
            safety = database.parent / ("before-restore-" + uid() + ".sqlite3")
            backup_database(database, safety)
            os.replace(temp, database)
            return safety
        finally:
            temp.unlink(missing_ok=True)


def report_csv(database, destination):
    # Explicit allowlist. Notes, account names, metadata, secrets and sessions stay private.
    with opened(database) as db, Path(destination).open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_id", "instrument_id", "task_id", "category", "completion_status", "occurred_at_utc", "original_timezone", "created_at_utc"])
        rows = db.execute("SELECT id,instrument_id,task_id,category,completion_status,occurred_at,original_timezone,created_at FROM events ORDER BY occurred_at,id")
        writer.writerows(rows)


@click.group()
@click.option("--data-dir", type=click.Path(path_type=Path), default=default_data_dir, show_default="platform user data directory")
@click.version_option(__version__)
@click.pass_context
def cli(ctx, data_dir):
    """Offline instrument maintenance. Data stays on this computer."""
    ctx.obj = data_dir.resolve()


def database_for(data_dir):
    database = data_dir / "mstracker.sqlite3"
    if not database.is_file():
        raise ValueError("Database not found. Run setup first with this --data-dir.")
    return database


@cli.command("setup")
@click.option("--name", prompt="Instrument name")
@click.option("--model", prompt="Instrument model")
@click.option("--timezone", "timezone_name", default="America/Chicago", prompt="IANA time zone")
@click.option("--weekday", type=click.IntRange(0, 6), prompt="Weekly tube-change day (0=Mon, 6=Sun)")
@click.option("--username", prompt="First account username")
@click.pass_obj
def setup_command(data_dir, name, model, timezone_name, weekday, username):
    """Configure one instrument and first account. Refuses existing databases."""
    password = click.prompt("Password (12+ characters)", hide_input=True, confirmation_prompt=True)
    setup_instance(data_dir, name, model, timezone_name, weekday, username, password)
    click.echo(f"Configured {name}. Database: {data_dir / 'mstracker.sqlite3'}")


@cli.command("user")
@click.argument("action", type=click.Choice(["create", "disable", "enable", "reset"]))
@click.argument("username")
@click.pass_obj
def user_command(data_dir, action, username):
    """Local-only account administration; no passwords on command lines."""
    database = database_for(data_dir)
    password = click.prompt("New password (12+ characters)", hide_input=True, confirmation_prompt=True) if action in ("create", "reset") else None
    change_user(database, username, action, password)
    click.echo(f"Account action completed: {action} {username}.")


@cli.command("serve")
@click.option("--port", type=click.IntRange(1024, 65535), default=8765, show_default=True)
@click.pass_obj
def serve_command(data_dir, port):
    """Run on loopback only, with one worker and no debug/reloader."""
    from waitress import serve
    database_for(data_dir)
    with process_lock(data_dir):
        app = create_app(data_dir)
        click.echo(f"MSTracker: http://127.0.0.1:{port} (Ctrl+C to stop)")
        serve(app, host="127.0.0.1", port=port, threads=1, connection_limit=32, channel_timeout=30, max_request_body_size=65536)


@cli.command("backup")
@click.argument("destination", type=click.Path(path_type=Path))
@click.pass_obj
def backup_command(data_dir, destination):
    """Write a consistent private SQLite backup to a NEW path."""
    backup_database(database_for(data_dir), destination)
    click.echo(f"Backup verified: {destination}")


@cli.command("restore")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.confirmation_option(prompt="Restore this instance from backup? Stop MSTracker first")
@click.pass_obj
def restore_command(data_dir, source):
    """Replace data from same-instance backup; keep a safety backup and revoke sessions."""
    safety = restore_database(database_for(data_dir), source)
    click.echo(f"Restored and verified. Previous data preserved at {safety}")


@cli.command("report")
@click.argument("destination", type=click.Path(path_type=Path))
@click.pass_obj
def report_command(data_dir, destination):
    """Create a minimal CSV report; excludes notes and credentials. Not interchange."""
    report_csv(database_for(data_dir), destination)
    click.echo(f"Minimal report saved: {destination}")


@cli.command("install")
@click.option("--destination", type=click.Path(path_type=Path))
def install_command(destination):
    """Install a self-contained bundle to a new per-user directory (Mac/Windows)."""
    from .deployment import install_bundle
    target = install_bundle(destination)
    click.echo(f"Installed: {target}\nNext: run the installed MSTracker executable with setup, then serve.")


@cli.command("autostart")
@click.argument("action", type=click.Choice(["enable", "disable", "show"]))
@click.option("--port", type=click.IntRange(1024, 65535), default=8765)
@click.pass_obj
def autostart_command(data_dir, action, port):
    """Configure per-user login auto-start for this instance on macOS or Windows."""
    from .deployment import autostart
    database_for(data_dir)
    click.echo(autostart(action, data_dir, port))


def main():
    try:
        cli()
    except (ValueError, OSError, sqlite3.Error) as exc:
        click.ClickException(str(exc)).show()
        raise SystemExit(1) from None
