"""Browsable SQLite storage and checksummed, atomic migrations."""
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from .timeutils import iso, utcnow


def uid():
    return str(uuid4())


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    return db


@contextmanager
def opened(path):
    db = connect(path)
    try:
        yield db
    finally:
        db.close()


def migrations():
    return sorted((Path(__file__).parent / "migrations").glob("*.sql"))


def migrate(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
        applied = {row["version"]: row["checksum"] for row in db.execute("SELECT * FROM schema_migrations")}
        files = migrations()
        versions = {int(p.name.split('_')[0]) for p in files}
        if not set(applied).issubset(versions):
            raise ValueError("Database schema is newer than this application; use the matching version.")
        for path in files:
            version = int(path.name.split('_')[0])
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            if version in applied:
                if applied[version] != checksum:
                    raise ValueError("Migration checksum mismatch; do not modify applied migrations.")
                continue
            statement = ""
            for line in sql.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    db.execute(statement)
                    statement = ""
            if statement.strip():
                raise ValueError("Incomplete migration statement.")
            db.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (version, checksum, iso(utcnow())))
        db.commit()
    except Exception:
        db.rollback()
        raise


def audit(db, actor, action, entity):
    db.execute("INSERT INTO audit VALUES (?,?,?,?,?)", (uid(), actor, action, entity, iso(utcnow())))


def instance(db):
    row = db.execute("SELECT * FROM instance WHERE singleton=1").fetchone()
    if row is None:
        raise ValueError("Instance is not configured. Run setup first.")
    return row


@contextmanager
def process_lock(data_dir):
    """Exclude a second server or restore while the server owns the data file."""
    import os
    path = Path(data_dir) / "server.lock"
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("Stop MSTracker before restoring or starting another server.") from None
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
