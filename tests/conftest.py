import re
from pathlib import Path

import pytest

from mstracker import create_app
from mstracker.cli import setup_instance
from mstracker.db import opened

PASSWORD = 'synthetic-test-password-123'


def hidden(response, name):
    return re.search(r'name="' + name + r'" value="([^"]+)"', response.get_data(as_text=True)).group(1)


@pytest.fixture
def configured(tmp_path):
    data = tmp_path / 'instrument'
    setup_instance(data, 'Synthetic Orbitrap', 'Exploris 480', 'America/Chicago', 2, 'ariana', PASSWORD)
    return data


@pytest.fixture
def app(configured):
    return create_app(configured, {'TESTING': True})


@pytest.fixture
def client(app):
    client = app.test_client()
    csrf = hidden(client.get('/login'), 'csrf_token')
    assert client.post('/login', data={'csrf_token': csrf, 'username': 'ariana', 'password': PASSWORD}).status_code == 302
    return client


def event_form(client, app, **updates):
    response = client.get('/events/new')
    with opened(app.config['DATABASE']) as db:
        task = db.execute('SELECT id FROM tasks ORDER BY id LIMIT 1').fetchone()[0]
    values = dict(csrf_token=hidden(response, 'csrf_token'), submission=hidden(response, 'submission'), task_id=task,
                  occurred_at='2025-01-15T14:30', completion_status='early', notes='Synthetic tube change')
    values.update(updates)
    return values
