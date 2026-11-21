import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.domain import (CONTRACT_R0, CONTRACT_R1, make_dataset, allocate,
                        validate, get_reference_sources, canonical)


def test_seed_variation_is_real():
    a,b=make_dataset(42),make_dataset(43)
    assert a['cases'] != b['cases']
    assert a['days'] == b['days'] == 4
    assert len(a['cases']) >= 12
    assert len(set(c['duration_hours'] for c in a['cases'])) >= 2
    assert len(set(c['required_skill'] for c in a['cases'])) == 3


@pytest.mark.parametrize('seed',[42,43,44,10042,10043,142,143,20042,20043])
def test_reference_valid_and_reduces_deadline_misses_fixed_hours(seed):
    data=make_dataset(seed)
    fifo=validate(data,allocate(data,policy='fifo'),policy='r0')
    edd=validate(data,allocate(data,policy='deadline'),policy='r1')
    assert fifo['valid'] and edd['valid']
    assert edd['missed_deadlines'] < fifo['missed_deadlines']
    assert edd['assigned_hours']==fifo['assigned_hours']
    assert edd['completed']==fifo['completed']==len(data['cases'])


def test_contracts_preserve_stable_requirement_id():
    assert CONTRACT_R0['id']==CONTRACT_R1['id']=="REQ-QUEUE-001"


def test_eligibility_caps_missing_and_durations_are_independent_hard_constraints():
    data=make_dataset(42)
    output=allocate(data,policy='deadline')
    bad=json.loads(canonical(output))
    bad['assignments'][0]['hours']=99
    assert not validate(data,bad)['valid']
    bad=json.loads(canonical(output))
    bad['assignments'][0]['reviewer_id']='UNKNOWN'
    assert not validate(data,bad)['valid']
    bad=json.loads(canonical(output))
    bad['assignments'].append(bad['assignments'][0])
    assert not validate(data,bad)['valid']
    bad=json.loads(canonical(output))
    bad['assignments'].pop()
    assert not validate(data,bad)['valid']
    bad=json.loads(canonical(output))
    bad['assignments'][0]['day']=True
    assert not validate(data,bad)['valid']
    assert not validate(data,output,policy='r0')['valid']


def test_reference_code_runs_standalone_in_python():
    d=make_dataset(44)
    with TemporaryDirectory() as tmp:
        for policy, code in zip(('fifo','deadline'),get_reference_sources()):
            Path(tmp,'input.json').write_text(json.dumps(d),encoding='utf-8')
            # Source scripts target E2B files. Change ONLY paths for local source contract unit test.
            path_code=code.replace('/home/user/input.json', f'{tmp}/input.json').replace('/home/user/output.json', f'{tmp}/output.json')
            Path(tmp,'solver.py').write_text(path_code,encoding='utf-8')
            res=subprocess.run([sys.executable, f'{tmp}/solver.py'],capture_output=True,text=True,timeout=8)
            assert res.returncode==0,res.stderr
            result=json.loads(Path(tmp,'output.json').read_text())
            assert result==allocate(d,policy=policy)
