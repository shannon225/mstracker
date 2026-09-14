# MSTracker

Offline maintenance history for one instrument, with named logins, routine/unplanned entries, a monthly calendar, a basic maintenance log, custom task definitions, and saved follow-up markers. The same Python application and tests run on **macOS and Windows 11**. Each instrument has its own instance and plain SQLite database. No web connection, CDN, telemetry, or hosted service is used at runtime.

## Run from source (Mac or Windows)

Use Python 3.11 or newer. Install on a development/test computer first. In the repository:

macOS Terminal:
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,build]'
.venv/bin/python -m mstracker --data-dir './local-data' setup
.venv/bin/python -m mstracker --data-dir './local-data' serve
```

Windows PowerShell (activation is not required):
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
.\.venv\Scripts\python.exe -m mstracker --data-dir ".\local-data" setup
.\.venv\Scripts\python.exe -m mstracker --data-dir ".\local-data" serve
```

Setup asks for instrument name/model, an IANA time zone (defaults to `America/Chicago`), weekly tube-change weekday (0=Monday through 6=Sunday), and first username/password. No production accounts or data are shipped. Passwords are entered through hidden prompts. Setup refuses to overwrite an existing database. If interrupted during initial setup, preserve the incomplete directory for diagnosis and use a new empty data directory.

Open [MSTracker locally](http://127.0.0.1:8765). Stop the foreground process with Ctrl+C. The server uses one Waitress worker plus its main thread, binds only to `127.0.0.1`, and has no debug/reloader. The browser consumes additional OS resources beyond this server budget. Different instances on one test computer need different `--data-dir` values and `serve --port` values. Browser cookies are named per instance.

`--data-dir` precedes the command. If omitted, storage is `~/Library/Application Support/MSTracker` on Mac or `%LOCALAPPDATA%\MSTracker` on Windows. Use an absolute data path for routine operation and auto-start. Keep code/bundles separate from data; install/update never intentionally modifies the database.

## Self-contained installation on either OS

The shared installer is a **command-line installer**, not a native graphical wizard. Build on the target OS/CPU; a Mac build cannot generate a Windows executable. On the connected build computer with the build dependencies installed:

```sh
python packaging/build.py
```

Use the virtual environment's Python executable from the source instructions. Copy the **entire** `dist/MSTracker` folder, including `_internal`, to the offline destination computer. Python need not be installed there. Keep dependency licenses included by the packager and the project LICENSE with the distribution. Build the Mac bundle using native Python for the intended CPU architecture; this round was checked with an x86_64 Mac Python runtime. Distribution signing/notarization is not configured.

Run the executable from the copied folder:

```sh
# macOS
./MSTracker install
# Windows PowerShell
.\MSTracker.exe install
```

Default install destinations are `~/Applications/MSTracker` on Mac and `%LOCALAPPDATA%\Programs\MSTracker` on Windows. To test without modifying those locations, add `--destination PATH`. Installation refuses existing targets. Then use the installed executable with `setup`, `serve`, `backup`, `user`, and the other commands instead of `python -m mstracker`:

```sh
# Example on Mac; on Windows use the installed MSTracker.exe path.
"$HOME/Applications/MSTracker/MSTracker" setup
"$HOME/Applications/MSTracker/MSTracker" serve
```

No dependency downloads occur during installation or app use. For source-only offline installation, prepare a platform-compatible wheelhouse and project wheel on a connected build machine, then use pip `--no-index --find-links WHEELHOUSE`. The bundled path is preferred for instrument PCs.

## Optional auto-start (Mac and Windows)

After installing and setting up, use the **installed** executable (or a stable installed Python environment):

```text
MSTracker --data-dir ABSOLUTE_DATA_PATH autostart show --port 8765
MSTracker --data-dir ABSOLUTE_DATA_PATH autostart enable --port 8765
MSTracker --data-dir ABSOLUTE_DATA_PATH autostart disable
```

Use `./MSTracker`, a full executable path, or `MSTracker.exe` as appropriate. `show` previews the configuration without changing startup. Mac uses a per-user LaunchAgent and starts it immediately; Windows uses a per-user HKCU Run entry at the next login. This is **user-login auto-start**, not a system service before login. Windows may display the packaged console. Disable before changing port/path, then enable from the new installed location. Stop a foreground instance before enabling auto-start. A second server is refused for the same data directory. Mac startup errors go to the data directory's `startup-error.log`; inspect and rotate it locally as needed. No persistent auto-start is enabled by the tests or installer.

## Accounts, time and maintenance behavior

- All active accounts can read history and create tasks/events. Account administration requires local file/command-line access: `user create NAME`, `user disable NAME`, `user enable NAME`, or `user reset NAME`. There is no separate web admin role. Disabling all accounts is recoverable locally with `user enable`.
- Passwords have a minimum of 12 characters and are stored only as salted scrypt hashes. Login attempts are limited; five failures for an account (or 30 total) in five minutes require waiting. Local reset clears that account's throttle and revokes its sessions. Disable/enable also revokes sessions. A reset never re-enables a disabled account.
- Signed, HttpOnly, SameSite=Strict session cookies last at most eight hours. Logout revokes the server-side session, so replaying the prior cookie does not restore access. Loopback HTTP cannot use the Secure cookie flag. Host restrictions, CSRF on POST, CSP and escaped notes protect the local web boundary. OS/file access can bypass web permissions; this is not protection from a hostile local administrator.
- `python reset_admin_password.py NAME --data-dir PATH` is the source recovery helper. Packaged installs use `MSTracker --data-dir PATH user reset NAME`; no Python installation or hidden web URL is needed.
- Occurrence defaults to the current instrument-local time and can be changed **before saving**. Future performed times and DST gaps are rejected; for a repeated fall-back hour choose the earlier/later occurrence. Actual UTC time, original local offset/zone/fold, creation time and author are retained separately. Time zone is fixed after setup in this round; recreate a test instance to change it, rather than editing a production database.
- Task definitions include name, details, category, expected minutes, one-time/weekly behavior and optional follow-up. The seeded weekly tube-change task uses the setup weekday. Early completion does not shift that weekly anchor. No automatic due-date/usage calculation exists yet. Tasks can be created; editing is deferred.
- Performed records are append-only. Database triggers reject updates/deletes to event/audit rows. This round has no correction/delete UI; add an explanatory new entry if necessary. A formal correction model needs a later plan.
- Follow-ups are orange dated calendar markers, not active notifications. Routine and unplanned records use blue/vermillion tints, separate icons and text labels. The calendar uses instrument-local dates; the log pages 50 records at a time. Notes appear only after sign-in.

## Backup, restore, reports and retention

Run with the same `--data-dir` used by the app:

```text
MSTracker --data-dir PATH backup NEW_BACKUP.sqlite3
MSTracker --data-dir PATH report NEW_REPORT.csv
MSTracker --data-dir PATH restore BACKUP.sqlite3
```

The SQLite backup API produces a consistent snapshot, including while the app runs; integrity is checked. Existing output files are never overwritten. Backups contain full history, private notes, credentials/hashes and session material: restrict access and keep a copy on approved offline media. Ordinary report CSVs contain only UUIDs, category/status and UTC/time-zone fields; they exclude notes, names, credentials, contacts, tokens, sessions and CSRF data. No expanded export option is provided. Report CSVs are not an InstrumentHub interchange format.

Restore requires a stopped server and explicit confirmation. Close DB Browser and any other SQLite connections too. It validates a disposable copy, rejects another instrument's backup, keeps a `before-restore-UUID.sqlite3` safety snapshot, replaces the database, rotates signing secrets, revokes all sessions and records the restore. The source backup is not modified. Backups preserve instance identity; never use one as a template for a different physical instrument. To move the same instrument to another computer, stop both apps, securely transfer the data directory, run the matching app version and perform a restore there before serving to revoke old sessions.

History and audit rows are retained indefinitely; no automatic purging occurs. Recommended operator policy: backup daily when used and before every update/restore; retain daily copies for 30 days and monthly copies according to lab policy. Copy off-device and periodically rehearse restoration on a test computer. Backup scheduling/retention automation is not shipped. Protect the data directory with OS account permissions and disk encryption as appropriate; the SQLite file itself is not encrypted/obfuscated and remains inspectable in DB Browser for SQLite.

Migrations are numbered SQL files with recorded checksums, run atomically. Newer schemas and changed applied migration files are rejected. Never edit applied migrations or modify the live schema manually. For an offline update: backup, disable auto-start, stop the app, install the new bundle into a new directory, verify a copy of the backup with the new version, start against the production data only after testing, then enable auto-start from the new executable. Keep the old bundle and backup. Do not open a migrated database with older code; roll back using the corresponding pre-update backup and app version.

## Validation and reviewer handoff

```sh
python -m pytest -q
python -m compileall -q mstracker reset_admin_password.py packaging
```

Use the platform's virtual-environment Python. Tests use temporary synthetic databases and no external services. The suite covers persistence, identity, DST, CSRF/host/session protections, task/event validation, backup/restore, secret exclusion and Mac/Windows startup adapters. Windows registry and macOS launchctl operations are simulated in the automated tests; an OS login test remains necessary.

See [canonical plan](docs/uu-first-round.md), [implementation record](docs/first-round-record.md), [task log](TASKS.md), [future exchange contract](docs/exchange-contract.md), and [platform acceptance checks](docs/platform-acceptance.md). Independent review and Ariana's final acceptance are pending. Windows installation, real login auto-start, offline operation, resource use and recovery must be verified on a non-instrument Windows 11 machine before instrument deployment. Mac package validation here does not certify Windows or all Mac CPU/OS combinations.

Deferred: advanced search/filtering, outages, automatic reminders, SST, service visits, manuals, sensitive instrument metadata, linked troubleshooting/images, due/overdue dashboards, event corrections and live InstrumentHub synchronization.
