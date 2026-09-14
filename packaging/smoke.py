"""Exercise a self-contained Mac/Windows bundle using temporary synthetic data.

Usage: python packaging/smoke.py /path/to/bundle/MSTracker[.exe]
Starts only temporary loopback servers; does not enable login auto-start.
"""
import html
import http.cookiejar
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

bundle = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='mstracker-package-smoke-') as work:
    root = Path(work)
    target = root/'Installed MSTracker'
    def run(executable, *args, input=None):
        result = subprocess.run([str(executable), *map(str,args)],input=input,text=True,capture_output=True,timeout=60)
        if result.returncode:
            raise RuntimeError(f'Command {args[0]} failed: {result.stderr}')
        return result.stdout
    run(bundle,'install','--destination',target)
    executable=target/bundle.name
    data=root/'Instrument Data'
    password='synthetic-package-password-123'
    run(executable,'--data-dir',data,'setup','--name','Synthetic instrument','--model','Orbitrap','--timezone','America/Chicago','--weekday','2','--username','smoke',input=password+'\n'+password+'\n')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def get(path):
        return opener.open(base+path,timeout=5).read().decode()
    def post(path,values):
        return opener.open(base+path,urllib.parse.urlencode(values).encode(),timeout=5).read().decode()
    def hidden(page,name):
        return html.unescape(re.search(r'name="'+name+r'" value="([^"]+)"',page).group(1))
    def start():
        process=subprocess.Popen([str(executable),'--data-dir',str(data),'serve','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if process.poll() is not None:
                raise RuntimeError(process.stderr.read().decode())
            try:
                get('/login');return process
            except (urllib.error.URLError,TimeoutError):
                time.sleep(.1)
        process.terminate();process.wait(timeout=10)
        raise RuntimeError('Packaged server did not start.')
    def stop(process):
        process.terminate();process.wait(timeout=10);process.stderr.close()
    process=start()
    try:
        login=get('/login')
        calendar=post('/login',dict(csrf_token=hidden(login,'csrf_token'),username='smoke',password=password))
        assert 'Maintenance calendar' in calendar
        form=get('/events/new')
        task=re.search(r'<option value="([0-9a-f-]{36})"',form).group(1)
        detail=post('/events/new',dict(csrf_token=hidden(form,'csrf_token'),submission=hidden(form,'submission'),task_id=task,occurred_at='2025-01-15T14:30',completion_status='early',notes='Synthetic packaged persistence check'))
        assert 'Synthetic packaged persistence check' in detail
        assert '14:30' in get('/?month=2025-01')
        assert 'Change ion transfer tube' in get('/log')
        if sys.platform=='darwin':
            print(subprocess.run(['ps','-M','-p',str(process.pid)],capture_output=True,text=True).stdout.strip())
            print(subprocess.run(['ps','-o','pid,rss,%cpu','-p',str(process.pid)],capture_output=True,text=True).stdout.strip())
        run(executable,'--data-dir',data,'backup',root/'backup.sqlite3')
    finally:
        stop(process)
    process=start()
    try:
        assert 'Change ion transfer tube' in get('/log')
        log=get('/log')
        assert 'Welcome back.' in post('/logout',{'csrf_token':hidden(log,'csrf_token')})
    finally:
        stop(process)
    run(executable,'--data-dir',data,'restore',root/'backup.sqlite3','--yes')
    run(executable,'--data-dir',data,'report',root/'report.csv')
    assert 'Synthetic packaged persistence check' not in (root/'report.csv').read_text()
    preview=run(executable,'--data-dir',data,'autostart','show')
    assert ('ProgramArguments' in preview) if sys.platform=='darwin' else ('--data-dir' in preview)
    print('PASS: self-contained install, setup, login, event/calendar/log, live backup, process restart, logout, restore, report and auto-start preview.')
