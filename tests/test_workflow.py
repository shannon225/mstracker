from datetime import timedelta

import pytest

from mstracker import create_app
from mstracker.cli import change_user
from mstracker.db import opened
from mstracker.timeutils import iso, utcnow
from conftest import PASSWORD, event_form, hidden


def test_complete_journey_and_restart(client, app, configured):
    values = event_form(client, app, notes='Changed tube. <script>alert(1)</script>')
    response = client.post('/events/new', data=values)
    assert response.status_code == 302
    detail = client.get(response.location).get_data(as_text=True)
    assert 'Changed tube.' in detail and '&lt;script&gt;' in detail and '<script>alert' not in detail
    assert 'ariana' in detail and '2025-01-15T14:30:00-06:00' in detail
    calendar = client.get('/?month=2025-01').get_data(as_text=True)
    assert 'Change ion transfer tube' in calendar and '14:30' in calendar
    with client.session_transaction() as session:
        saved = dict(session)
    restarted = create_app(configured, {'TESTING': True}).test_client()
    with restarted.session_transaction() as session:
        session.update(saved)
    assert 'Change ion transfer tube' in restarted.get('/log').get_data(as_text=True)
    csrf = hidden(restarted.get('/log'), 'csrf_token')
    assert restarted.post('/logout', data={'csrf_token': csrf}).status_code == 302
    assert restarted.get('/log').location.endswith('/login')
    # Replaying the pre-logout signed state must fail server-side.
    with restarted.session_transaction() as session:
        session.update(saved)
    assert restarted.get('/log').location.endswith('/login')
    with opened(app.config['DATABASE']) as db:
        event = db.execute('SELECT * FROM events').fetchone()
        assert event['occurred_at'] == '2025-01-15T20:30:00Z'
        assert event['created_at'] > event['occurred_at']
        assert event['revision'] == 1


def test_duplicate_form_and_separate_tabs(client, app):
    first, second = event_form(client, app), event_form(client, app)
    response = client.post('/events/new', data=first)
    assert client.post('/events/new', data=first).location == response.location
    assert client.post('/events/new', data=second).status_code == 302
    with opened(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0] == 2


def test_unplanned_task_and_followup(client, app):
    future = (utcnow() + timedelta(days=4)).strftime('%Y-%m-%dT12:00')
    response = client.get('/tasks')
    data = dict(csrf_token=hidden(response,'csrf_token'), name='Investigate pressure', details='Error code recorded', category='unplanned',
                expected_minutes='45', recurrence='one-time', follow_up=future)
    assert client.post('/tasks', data=data).status_code == 302
    with opened(app.config['DATABASE']) as db:
        task = db.execute("SELECT * FROM tasks WHERE category='unplanned'").fetchone()
        task_id = task['id']
        assert task['follow_up_at'] is not None and task['weekday'] is None
    values = event_form(client, app, task_id=task_id, follow_up=future, completion_status='anything')
    response = client.post('/events/new', data=values)
    assert response.status_code == 302
    assert 'Follow-up' in client.get(response.location).get_data(as_text=True)
    with opened(app.config['DATABASE']) as db:
        assert db.execute('SELECT completion_status FROM events').fetchone()[0] == 'unplanned'
        assert db.execute('SELECT count(*) FROM calendar_markers').fetchone()[0] == 2
    calendar = client.get('/?month=' + future[:7]).get_data(as_text=True)
    assert 'Investigate pressure' in calendar and '⚑ Follow-up' in calendar


@pytest.mark.parametrize('changes,message', [
    ({'occurred_at':'2099-01-01T00:00'}, 'future'),
    ({'occurred_at':'2025-03-09T02:30'}, 'does not exist'),
    ({'occurred_at':'2025-11-02T01:30'}, 'occurs twice'),
    ({'occurred_at':'garbage'}, 'valid date'),
    ({'completion_status':'unplanned'}, 'on-time or early'),
    ({'task_id':'missing'}, 'existing task'),
    ({'notes':'x'*10001}, '10000'),
    ({'follow_up':'2020-01-01T00:00'}, 'later than now'),
    ({'submission':'fake'}, 'expired'),
])
def test_event_validation_is_atomic(client, app, changes, message):
    response = client.post('/events/new', data=event_form(client, app, **changes))
    assert response.status_code == 400 and message in response.get_data(as_text=True)
    with opened(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM calendar_markers').fetchone()[0] == 0


def test_dst_choices_and_local_calendar_date(client, app):
    for fold in ('0','1'):
        assert client.post('/events/new', data=event_form(client, app, occurred_at='2025-11-02T01:30', fold=fold)).status_code == 302
    assert client.post('/events/new', data=event_form(client, app, occurred_at='2025-01-31T23:30')).status_code == 302
    with opened(app.config['DATABASE']) as db:
        rows = db.execute("SELECT occurred_at FROM events WHERE original_local_time LIKE '2025-11-02%' ORDER BY occurred_at").fetchall()
        assert [row[0] for row in rows] == ['2025-11-02T06:30:00Z','2025-11-02T07:30:00Z']
    assert '23:30' in client.get('/?month=2025-01').get_data(as_text=True)


def test_auth_csrf_host_and_headers(app, client):
    anonymous = app.test_client()
    for path in ('/', '/log', '/tasks', '/events/new'):
        assert anonymous.get(path).status_code == 302
    assert anonymous.post('/login', data={'username':'ariana','password':PASSWORD}).status_code == 400
    assert client.post('/events/new', data={}).status_code == 400
    assert client.get('/log', headers={'Host':'attacker.example'}).status_code == 400
    response = client.get('/log')
    assert 'no-store' in response.headers['Cache-Control']
    assert "script-src 'none'" in response.headers['Content-Security-Policy']
    assert response.headers['X-Frame-Options'] == 'DENY'


@pytest.mark.parametrize('action', ['disable','reset'])
def test_account_changes_revoke_existing_sessions(client, app, action):
    change_user(app.config['DATABASE'], 'ariana', action, PASSWORD+'new' if action=='reset' else None)
    assert client.get('/log').status_code == 302
    if action == 'disable':
        change_user(app.config['DATABASE'],'ariana','enable')
        assert client.get('/log').status_code == 302


def test_named_users_and_throttle(app):
    change_user(app.config['DATABASE'],'second','create',PASSWORD)
    client=app.test_client()
    for number in range(5):
        token=hidden(client.get('/login'),'csrf_token')
        response=client.post('/login',data={'csrf_token':token,'username':'second','password':'wrong'})
        assert response.status_code==401
    token=hidden(client.get('/login'),'csrf_token')
    assert client.post('/login',data={'csrf_token':token,'username':'second','password':PASSWORD}).status_code==429
    change_user(app.config['DATABASE'],'second','reset',PASSWORD)
    assert client.post('/login',data={'csrf_token':token,'username':'second','password':PASSWORD}).status_code==302
    assert client.post('/events/new',data=event_form(client,app)).status_code==302
    assert 'second' in client.get('/log').get_data(as_text=True)


def test_session_expiration(client,app):
    with opened(app.config['DATABASE']) as db:
        with db:
            db.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00Z'")
    assert client.get('/log').status_code==302


def test_invalid_navigation_and_task_validation(client,app):
    for path in ('/?month=garbage','/?month=9999-12','/log?page=0','/log?page=no'):
        assert client.get(path).status_code==400
    assert client.get('/events/not-found').status_code==404
    data=dict(csrf_token=hidden(client.get('/tasks'),'csrf_token'),name='Custom',category='routine',expected_minutes='0',recurrence='weekly',weekday='9')
    assert client.post('/tasks',data=data).status_code==400
    with opened(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM tasks').fetchone()[0]==1


def test_event_marker_failure_rolls_back_event_and_audit(client,app,monkeypatch):
    import mstracker.web as web
    def fail_marker(*args,**kwargs):
        raise ValueError('Synthetic marker failure')
    monkeypatch.setattr(web,'add_marker',fail_marker)
    future=(utcnow()+timedelta(days=3)).strftime('%Y-%m-%dT12:00')
    response=client.post('/events/new',data=event_form(client,app,follow_up=future))
    assert response.status_code==400
    with opened(app.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM audit WHERE action='event_created'").fetchone()[0]==0


def test_log_pagination_has_no_overlap(client,app):
    for number in range(51):
        assert client.post('/events/new',data=event_form(client,app,notes=f'Synthetic event {number}')).status_code==302
    import re
    first=client.get('/log').get_data(as_text=True)
    second=client.get('/log?page=2').get_data(as_text=True)
    first_ids=set(re.findall(r'href="/events/([0-9a-f-]{36})"',first))
    second_ids=set(re.findall(r'href="/events/([0-9a-f-]{36})"',second))
    assert len(first_ids)==50 and len(second_ids)==1 and first_ids.isdisjoint(second_ids)
