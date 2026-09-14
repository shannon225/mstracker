CREATE TABLE instance (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    id TEXT NOT NULL UNIQUE, instrument_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL, model TEXT NOT NULL, timezone TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    external_reference TEXT CHECK(external_reference IS NULL OR json_valid(external_reference)),
    secret_key TEXT NOT NULL
);
CREATE TABLE users (
    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at TEXT NOT NULL
);
CREATE TABLE tasks (
    id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL REFERENCES instance(instrument_id),
    name TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL CHECK(category IN ('routine','unplanned')),
    expected_minutes INTEGER NOT NULL CHECK(expected_minutes BETWEEN 1 AND 10080),
    recurrence TEXT NOT NULL CHECK(recurrence IN ('one-time','weekly')),
    weekday INTEGER CHECK(weekday BETWEEN 0 AND 6),
    follow_up_at TEXT, created_by TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    external_reference TEXT CHECK(external_reference IS NULL OR json_valid(external_reference)),
    CHECK((recurrence='weekly' AND weekday IS NOT NULL) OR (recurrence='one-time' AND weekday IS NULL))
);
CREATE TABLE events (
    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
    instrument_id TEXT NOT NULL REFERENCES instance(instrument_id),
    category TEXT NOT NULL CHECK(category IN ('routine','unplanned')),
    completion_status TEXT NOT NULL CHECK(completion_status IN ('on-time','early','unplanned')),
    occurred_at TEXT NOT NULL, original_local_time TEXT NOT NULL,
    original_timezone TEXT NOT NULL, original_fold INTEGER NOT NULL CHECK(original_fold IN (0,1)),
    notes TEXT NOT NULL DEFAULT '', performed_by TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    external_reference TEXT CHECK(external_reference IS NULL OR json_valid(external_reference)),
    submission_key TEXT NOT NULL UNIQUE,
    CHECK((category='routine' AND completion_status IN ('on-time','early')) OR
          (category='unplanned' AND completion_status='unplanned'))
);
CREATE INDEX events_occurred ON events(occurred_at DESC, id);
CREATE TABLE calendar_markers (
    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
    event_id TEXT REFERENCES events(id), instrument_id TEXT NOT NULL REFERENCES instance(instrument_id),
    due_at TEXT NOT NULL, timezone TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind='follow-up'),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    external_reference TEXT CHECK(external_reference IS NULL OR json_valid(external_reference))
);
CREATE INDEX markers_due ON calendar_markers(due_at);
CREATE TABLE audit (
    id TEXT PRIMARY KEY, actor_id TEXT REFERENCES users(id), action TEXT NOT NULL,
    entity_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL
);
CREATE TABLE login_attempts (
    username TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_start TEXT NOT NULL
);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'Events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'Events are append-only'); END;
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append-only'); END;
