# Platform acceptance before instrument deployment

Use synthetic data on a non-instrument computer. Run on each supported OS/CPU distribution. The app, command-line installer and optional login auto-start share the same commands; native OS integration differs.

| Check | Expected evidence | This implementation host |
|---|---|---|
| Source suite and compile | All tests pass on Python 3.11+ | macOS tested; Windows pending |
| Self-contained build/install | New destination has executable/runtime/assets; existing targets refused | macOS x86_64 build/install tested; Windows pending |
| Offline setup and browse | Unplug network; configure instrument/account; login/create/view/logout | Runtime uses local assets; physical disconnect test pending |
| Process restart | Event retains original time/author/notes; calendar/log agree | Automated app restart and HTTP checks |
| Auto-start | At OS login one instance starts with correct data/port; disabling survives login | Generated configurations and mocked adapters tested; real OS-login test pending on both OSs |
| Resource budget | Measure server thread count, idle/busy CPU/RSS; include browser separately | See implementation record for local sample; Windows pending |
| Durability | Backup during writes; stop, restore and check identity/history/revocation | Automated SQLite backup/restore tests; power-loss simulation pending |
| Update and rollback | Install side-by-side, verify copied data, migrate, restore old version/backup if needed | Procedure documented; cross-version rehearsal pending |
| Failure recovery | Occupied port, duplicate server, bad data path, read-only/full disk, missing/corrupt/newer-schema DB show useful failure | Selected automated failure cases tested; full platform matrix pending |
| OS trust/distribution | Verify architecture, signatures/trusted distribution process, permissions and dependencies | Local development bundle only; signing/notarization not configured |

Mac LaunchAgents run in the logged-in user's session, not at boot before login. Windows HKCU Run entries behave similarly. Enabling auto-start is an explicit operator action. The installer does not enable it or create production credentials.
