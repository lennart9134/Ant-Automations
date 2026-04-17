# desktop-agent

**Runtime:** Tauri 2.x (Rust + WebView).
**Target platforms:** macOS, Windows, Linux.
**Role:** Watch-layer client. Captures application-level interaction patterns (app switches,
window focus changes, file open/save patterns, time-on-task) and forwards them to
`services/observation-ingest`.

## Scope (Business Plan v4.5 §4.1.1)

- Run as a background service on the employee's machine (~50 MB RAM, <1% CPU).
- Capture **metadata events only** — no keystroke logging, no clipboard content, no screen
  recording by default.
- System-tray indicator shows observation status: active / paused / disabled.
- Employee can pause observation at any time from the tray menu.
- Configurable capture scope per deployment: minimal (app switches only), application
  (app + window focus), action (app + window + file open/save).

## Why Tauri over Electron

- Memory footprint ~50 MB vs Electron's 150–300 MB — critical for endpoint deployment on
  employee machines running many other apps.
- Rust-first, smaller attack surface, better suited to security review in regulated sectors.
- Signed cross-platform builds via Tauri's built-in bundler.

See [ADR 006](../../docs/adr/006-tauri-desktop-agent.md) for the full decision record.

## Current state

Scaffold. Includes:

- `src-tauri/tauri.conf.json` — Tauri configuration with a hidden main window and a system-tray
  icon.
- `src-tauri/src/main.rs` — entrypoint: registers tray, starts a heartbeat task that emits an
  event on an interval.
- `src-tauri/src/events.rs` — defines the `ObservationEvent` struct that mirrors the wire schema
  in `services/observation-ingest`.
- `src-tauri/src/ingest.rs` — HTTP POST client that batches events to
  `POST /api/v1/events/batch` on the ingest service.
- `src-tauri/Cargo.toml` — dependency list.
- `ui/` — minimal HTML for the settings window (pause toggle, scope selector, status).

### Next-step TODOs

- [ ] Implement platform-specific capture backends:
  - macOS: `NSWorkspace` notifications for app activation / deactivation.
  - Windows: `SetWinEventHook` for foreground window changes.
  - Linux (X11 and Wayland): varies by compositor — start with X11.
- [ ] Wire the pause button in the tray menu to stop emission.
- [ ] Add signed build pipeline (`tauri build` on GitHub Actions for all three platforms).
- [ ] Implement the employee transparency dashboard HTML (shows aggregate stats for the
      observed employee only — their own event count, last event time, categories captured).
- [ ] Add exponential-backoff retry for ingest failures (agent must never silently lose events
      or silently spin-retry).
- [ ] Code-sign and notarise builds (macOS Developer ID, Windows Authenticode).

## Development

```bash
cd clients/desktop-agent
cargo install tauri-cli --version "^2.0"
cargo tauri dev
```

You need a local `observation-ingest` running at `http://localhost:8006` for events to be
delivered. With no ingest available the agent logs to stderr and keeps trying.

## Privacy & compliance

This client is subject to:

- [ADR 006](../../docs/adr/006-tauri-desktop-agent.md) — technology decision.
- [Betriebsvereinbarung template](../../docs/security/betriebsvereinbarung-template.md) — works
  council agreement required before deployment in Germany.
- [Instemmingsverzoek template](../../docs/security/instemmingsverzoek-template.md) — works
  council consent required before deployment in the Netherlands.
- [DPIA — observation layer](../../docs/security/dpia-observation-layer.md).
- [Employee privacy notice template](../../docs/security/employee-privacy-notice.md).

Do not deploy this agent to any customer until the customer has signed the applicable works
council documents. This is not a legal-formality step. It is a mandatory co-determination right
under BetrVG §87(1) Nr. 6 (Germany) / WOR Art. 27(1)(l) (Netherlands).
