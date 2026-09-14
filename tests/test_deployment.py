from pathlib import Path
import plistlib
import sys
import types

import pytest

from mstracker import deployment


def test_mac_launch_arguments_preserve_spaces(tmp_path):
    data = tmp_path/'Instrument Data'
    command = deployment.launch_command(data,8765,executable='/Applications/MSTracker folder/MSTracker',frozen=True)
    payload = deployment.mac_plist(data,8765,command)
    decoded = plistlib.loads(plistlib.dumps(payload))
    assert decoded['ProgramArguments']==command
    assert command==['/Applications/MSTracker folder/MSTracker','--data-dir',str(data.resolve()),'serve','--port','8765']
    assert decoded['RunAtLoad'] and 'KeepAlive' not in decoded
    assert deployment.startup_id(data)!=deployment.startup_id(tmp_path/'other')


def test_mac_enable_disable_configuration(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,'platform','darwin')
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    commands=[]
    monkeypatch.setattr(deployment.subprocess,'run',lambda command,**kwargs:(commands.append(command) or types.SimpleNamespace(returncode=0,stderr='')))
    data=tmp_path/'data'
    assert 'plist' in deployment.autostart('show',data,8765)
    deployment.autostart('enable',data,8765)
    path=tmp_path/'Library/LaunchAgents'/(deployment.startup_id(data)+'.plist')
    assert path.exists() and commands[0][1]=='bootstrap'
    with pytest.raises(ValueError,match='already'):
        deployment.autostart('enable',data,8765)
    deployment.autostart('disable',data,8765)
    assert not path.exists() and commands[-1][1]=='bootout'


def test_windows_run_entry_and_quoting(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setattr(sys,'executable',r'C:\Program Files\MSTracker\MSTracker.exe')
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    values={}
    class Key:
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def query(key,name):
        if name not in values:raise FileNotFoundError
        return values[name],1
    registry=types.SimpleNamespace(HKEY_CURRENT_USER=1,REG_SZ=1,CreateKey=lambda *args:Key(),QueryValueEx=query,
        SetValueEx=lambda key,name,unused,kind,value:values.update({name:value}),DeleteValue=lambda key,name:values.pop(name))
    monkeypatch.setitem(sys.modules,'winreg',registry)
    data=tmp_path/'Data With Spaces'
    preview=deployment.autostart('show',data,8765)
    assert preview.startswith('"C:\\Program Files\\MSTracker\\MSTracker.exe"')
    deployment.autostart('enable',data,8765)
    assert values[deployment.startup_id(data)]==preview
    with pytest.raises(ValueError,match='already'):
        deployment.autostart('enable',data,8765)
    deployment.autostart('disable',data,8765)
    assert not values


def test_shared_installer_refuses_overwrite(tmp_path,monkeypatch):
    source=tmp_path/'bundle';source.mkdir()
    executable=source/'MSTracker';executable.write_text('synthetic executable')
    (source/'_internal').mkdir();(source/'_internal/asset').write_text('asset')
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'executable',str(executable))
    target=deployment.install_bundle(tmp_path/'Applications/MSTracker')
    assert (target/'_internal/asset').read_text()=='asset'
    with pytest.raises(ValueError,match='already exists'):
        deployment.install_bundle(target)
    with pytest.raises(ValueError,match='outside'):
        deployment.install_bundle(source/'inside')
