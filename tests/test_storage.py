import json
import sqlite3
from pathlib import Path

import pytest

from mstracker import create_app
from mstracker.cli import backup_database, password_hash, report_csv, restore_database, setup_instance
from mstracker.db import migrate, opened, process_lock
from mstracker.timeutils import local_instant
from conftest import PASSWORD, event_form


def test_migrations_idempotent_checksummed_and_future_rejection(configured):
    with opened(configured/'mstracker.sqlite3') as db:
        migrate(db)
        assert db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0]==1
        with db:
            db.execute("UPDATE schema_migrations SET checksum='changed'")
        with pytest.raises(ValueError,match='checksum'):
            migrate(db)
        with db:
            db.execute("INSERT INTO schema_migrations VALUES (999,'future','2025-01-01T00:00:00Z')")
        with pytest.raises(ValueError,match='newer'):
            migrate(db)


def test_failed_migration_rolls_back(tmp_path,monkeypatch):
    import mstracker.db as module
    migration=tmp_path/'001_broken.sql'
    migration.write_text('CREATE TABLE partial (id INTEGER);\nTHIS IS INVALID;\n')
    monkeypatch.setattr(module,'migrations',lambda:[migration])
    with opened(tmp_path/'test.sqlite3') as db:
        with pytest.raises(sqlite3.Error):
            migrate(db)
        assert not db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_setup_refuses_overwrite_and_isolates_instances(configured,tmp_path):
    with pytest.raises(FileExistsError):
        setup_instance(configured,'New','Other','America/Chicago',0,'other',PASSWORD)
    second=tmp_path/'second'
    setup_instance(second,'Second','Other','America/Chicago',4,'other',PASSWORD)
    with opened(configured/'mstracker.sqlite3') as first,opened(second/'mstracker.sqlite3') as other:
        assert first.execute('SELECT id FROM instance').fetchone()[0]!=other.execute('SELECT id FROM instance').fetchone()[0]
        assert first.execute('SELECT username FROM users').fetchone()[0]=='ariana'
    with pytest.raises(ValueError,match='another instrument'):
        restore_database(configured/'mstracker.sqlite3',second/'mstracker.sqlite3')


def test_backup_restore_retains_history_revokes_sessions(client,app,configured,tmp_path):
    client.post('/events/new',data=event_form(client,app,notes='PRIVATE_NOTE_123'))
    database=app.config['DATABASE']
    backup=tmp_path/'backup.sqlite3'
    backup_database(database,backup)
    with pytest.raises(FileExistsError):
        backup_database(database,backup)
    client.post('/events/new',data=event_form(client,app,notes='After backup'))
    safety=restore_database(database,backup)
    with opened(database) as db,opened(safety) as old:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==1
        assert old.execute('SELECT count(*) FROM events').fetchone()[0]==2
        assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==0
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute("SELECT count(*) FROM audit WHERE action='local_restore'").fetchone()[0]==1
    restarted=create_app(configured,{'TESTING':True})
    assert restarted.test_client().get('/log').status_code==302
    with process_lock(configured):
        with pytest.raises(ValueError,match='Stop MSTracker'):
            restore_database(database,backup)


def test_report_allowlist_and_no_overwrite(client,app,tmp_path):
    client.post('/events/new',data=event_form(client,app,notes='PRIVATE_NOTE_123'))
    output=tmp_path/'report.csv'
    report_csv(app.config['DATABASE'],output)
    text=output.read_text()
    assert '2025-01-15T20:30:00Z' in text
    for forbidden in ('PRIVATE_NOTE_123','ariana','password','scrypt','token','csrf','session','secret','Synthetic Orbitrap'):
        assert forbidden not in text
    with pytest.raises(FileExistsError):
        report_csv(app.config['DATABASE'],output)


def test_append_only_history(client,app):
    client.post('/events/new',data=event_form(client,app))
    with opened(app.config['DATABASE']) as db:
        for statement in ('DELETE FROM events',"UPDATE events SET notes='changed'",'DELETE FROM audit',"UPDATE audit SET action='changed'"):
            with pytest.raises(sqlite3.IntegrityError,match='append-only'):
                db.execute(statement)
            db.rollback()


def test_password_and_time_validation():
    with pytest.raises(ValueError):
        password_hash('short')
    assert password_hash(PASSWORD)!=password_hash(PASSWORD)
    with pytest.raises(ValueError,match='IANA'):
        local_instant('2025-01-01T00:00','Not/AZone')
    assert local_instant('2025-01-01T00:00','UTC')[0]=='2025-01-01T00:00:00Z'


def test_corrupt_restore_preserves_live_database(configured,tmp_path):
    database=configured/'mstracker.sqlite3'
    original=database.read_bytes()
    corrupt=tmp_path/'corrupt.sqlite3';corrupt.write_bytes(b'not sqlite')
    with pytest.raises(sqlite3.DatabaseError):
        restore_database(database,corrupt)
    assert database.read_bytes()==original
