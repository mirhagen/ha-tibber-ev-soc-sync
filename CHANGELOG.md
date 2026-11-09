# Changelog

## 0.1.0 – 2026-11-09

First version.

- Sends the EV's battery level to Tibber for cars without Tibber integration ("Brand offline").
- Syncs when the charging cable is plugged in, and again when the level changes while plugged in.
- *Sync now* button, `tibber_ev_soc_sync.sync` action, sensors for battery level in Tibber, last successful sync and sync status.
- Re-authentication when Tibber rejects the login, diagnostics with redacted credentials.
- English and Swedish.
