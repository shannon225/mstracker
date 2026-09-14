import json
from datetime import datetime
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo


def test_synthetic_contract_replay_states_dst_and_allowlist():
    fixture=json.loads((Path(__file__).parent/'fixtures/exchange-v0.1.json').read_text())
    assert fixture['contract_version']=='0.1'
    UUID(fixture['source_instance_id'])
    seen={}
    for record in fixture['records']:
        UUID(record['id']);UUID(record['instrument_id'])
        assert record['revision']>=1 and record['expected_minutes']>0
        key=record['idempotency_key']
        assert key==f"{fixture['source_instance_id']}:{record['entity_type']}:{record['id']}:{record['revision']}"
        if key in seen:
            assert record==seen[key]
        seen[key]=record
        for field in ('created_at','updated_at'):
            assert record[field].endswith('Z')
            datetime.fromisoformat(record[field])
    assert len(seen)==len(fixture['records'])-1
    occurrences=[r for r in seen.values() if r['entity_type']=='task_occurrence']
    assert {r['state'] for r in occurrences}=={'completed','skipped'}
    assert next(r for r in occurrences if r['state']=='skipped')['performed_event_id'] is None
    event=next(r for r in seen.values() if r['entity_type']=='performed_event')
    actual=datetime.fromisoformat(event['occurred_at']).astimezone(ZoneInfo(fixture['timezone']))
    assert actual.isoformat()==event['original_local_time'] and actual.fold==1
    def inspect(value):
        if isinstance(value,dict):
            assert not (set(value)&{'password','password_hash','secret_key','session','sessions','csrf','csrf_token','token','notes','contacts'})
            for item in value.values():inspect(item)
        if isinstance(value,list):
            for item in value:inspect(item)
    inspect(fixture)
