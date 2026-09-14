"""Common installation interface with small native auto-start adapters."""
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


def launch_command(data_dir, port, executable=None, frozen=None):
    executable = executable or sys.executable
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    return [str(executable)] + ([] if frozen else ["-m", "mstracker"]) + ["--data-dir", str(Path(data_dir).resolve()), "serve", "--port", str(port)]


def startup_id(data_dir):
    key = hashlib.sha256(str(Path(data_dir).resolve()).encode()).hexdigest()[:16]
    return "org.mstracker." + key


def mac_plist(data_dir, port, command=None):
    data_dir = Path(data_dir).resolve()
    return {
        "Label": startup_id(data_dir), "ProgramArguments": command or launch_command(data_dir, port),
        "WorkingDirectory": str(data_dir), "RunAtLoad": True,
        "StandardOutPath": "/dev/null", "StandardErrorPath": str(data_dir / "startup-error.log"),
        # No restart loop if setup is missing, port is occupied, or migration fails.
    }


def install_bundle(destination=None):
    if not getattr(sys, "frozen", False):
        raise ValueError("The install command requires a self-contained bundle. For source use pip install .")
    source = Path(sys.executable).resolve().parent
    if destination is None:
        if sys.platform == "darwin":
            destination = Path.home() / "Applications/MSTracker"
        elif sys.platform == "win32":
            destination = Path(os.environ["LOCALAPPDATA"]) / "Programs/MSTracker"
        else:
            raise ValueError("Packaged installation supports macOS and Windows.")
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents:
        raise ValueError("Destination must be outside the distribution directory.")
    if destination.exists():
        raise ValueError("Destination already exists. Install an update into a new directory; preserve the old version.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return destination


def autostart(action, data_dir, port):
    command = launch_command(data_dir, port)
    label = startup_id(data_dir)
    if sys.platform == "darwin":
        path = Path.home() / "Library/LaunchAgents" / (label + ".plist")
        payload = mac_plist(data_dir, port, command)
        if action == "show":
            return plistlib.dumps(payload).decode()
        domain = f"gui/{os.getuid()}"
        if action == "disable":
            if not path.exists():
                return "Auto-start is already disabled."
            # bootout can report not loaded after reboot; removal still disables next login.
            subprocess.run(["launchctl", "bootout", domain, str(path)], capture_output=True, check=False)
            path.unlink()
            return "Auto-start disabled; stop any manually started server separately."
        if path.exists():
            raise ValueError("Auto-start already configured. Disable it before enabling with new settings.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            plistlib.dump(payload, handle)
        result = subprocess.run(["launchctl", "bootstrap", domain, str(path)], capture_output=True, text=True)
        if result.returncode:
            path.unlink()
            raise ValueError("launchctl could not enable auto-start: " + result.stderr.strip())
        return "Auto-start enabled for this user at login. Verify the local calendar opens."
    if sys.platform == "win32":
        import winreg
        # pythonw hides the source-install console; frozen bundle retains its console.
        if not getattr(sys, "frozen", False):
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            if pythonw.exists():
                command[0] = str(pythonw)
        value = subprocess.list2cmdline(command)
        if action == "show":
            return value
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            if action == "disable":
                try:
                    winreg.DeleteValue(key, label)
                except FileNotFoundError:
                    pass
                return "Auto-start disabled for future logins. Stop the current server separately."
            try:
                winreg.QueryValueEx(key, label)
            except FileNotFoundError:
                winreg.SetValueEx(key, label, 0, winreg.REG_SZ, value)
            else:
                raise ValueError("Auto-start already configured. Disable it before enabling with new settings.")
        return "Auto-start enabled for this user at the next login."
    raise ValueError("Auto-start supports macOS and Windows only.")
