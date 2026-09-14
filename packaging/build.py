"""Run on each target OS/CPU: python packaging/build.py. No downloads at runtime."""
from pathlib import Path
import platform
import subprocess
import sys
import shutil

root = Path(__file__).resolve().parents[1]
if sys.platform not in ('darwin', 'win32'):
    raise SystemExit('Build this distribution on macOS or Windows.')
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
    '--name', 'MSTracker', '--paths', str(root), '--collect-all', 'mstracker',
    '--collect-data', 'tzdata', '--distpath', str(root/'dist'),
    '--workpath', str(root/'build/pyinstaller'), '--specpath', str(root/'build'),
    str(root/'packaging/entrypoint.py'),
], check=True, cwd=root)
shutil.copy2(root/'LICENSE', root/'dist/MSTracker/LICENSE')
shutil.copy2(root/'README.md', root/'dist/MSTracker/README.md')
print(f'Bundle: {root / "dist/MSTracker"} ({sys.platform}, {platform.machine()}).')
print('Distribute the entire folder, including _internal. Run MSTracker install from that folder.')
