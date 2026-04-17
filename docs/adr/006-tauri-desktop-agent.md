# ADR 006: Tauri for the desktop observation agent

## Status
Accepted

## Context
The Watch layer of the v4.5 platform (Business Plan §4.1.1, §11A.5) requires
a long-running agent on employee macOS and Windows laptops. The agent must:

- Emit observation events (application switches, window focus, file
  events) to the ingest service with <1% CPU overhead and <100 MB RAM —
  laptops that are already running Teams, Slack, and a full IDE can't
  afford a heavyweight observer.
- Expose a system-tray transparency UI with a pause toggle that takes
  effect immediately (mandated by the DE Betriebsvereinbarung template
  §4 and NL instemmingsverzoek §3).
- Be code-signable for Windows (Authenticode) and macOS (Developer ID +
  notarisation), because customer endpoint protection will quarantine
  anything that isn't.
- Ship auto-update so we can close CVEs without an IT-driven redeploy on
  thousands of employee laptops.

Options considered:

1. **Electron** — familiar to the team; well-supported auto-update; huge
   install footprint (~150–300 MB RAM at idle with the Chromium renderer)
   and a track record of being flagged by endpoint protection.
2. **Tauri 2.x** (Rust core + OS-native WebView) — ~50 MB RAM at idle,
   native OS APIs accessible from Rust (which matters for the macOS
   `NSWorkspace` and Windows `SetWinEventHook` capture backends).
3. **Pure Go with a systray library + no UI** — smallest footprint, but
   no path to the transparency UI the works council requires.
4. **Native Swift + C# per-platform** — best performance and platform
   fit, but doubles engineering cost for what is mostly a background
   service.

## Decision
Use **Tauri 2.x** for the desktop observation agent. The Rust core handles
platform capture backends, event batching, and the HTTP ingest client. A
small HTML/CSS transparency UI is rendered via the OS-native WebView (no
bundled Chromium).

## Rationale
- **Footprint.** Idle-state memory is in the right order of magnitude
  for laptops already running enterprise software. Electron was a
  non-starter once we added the 50 MB cap implicit in §11A.5.
- **Platform APIs from Rust.** The capture backends need direct access
  to `NSWorkspace` notifications (macOS) and `SetWinEventHook`
  (Windows). Both are cleaner from Rust via the `cocoa` / `windows`
  crates than from the Electron main process.
- **Code-signing and notarisation are first-class.** Tauri's bundler
  integrates with Apple notarisation and Authenticode; we don't have to
  build a signing pipeline from scratch.
- **WebView-based UI is enough.** The transparency panel doesn't need
  complex UI; the system tray is the primary surface. A ~50 KB HTML page
  is all we need.
- **Security posture.** Tauri's allowlist model restricts which OS APIs
  the WebView can reach. Our UI needs none of them — we can lock the
  WebView down to `shell: false, fs: false, http: false`, etc., which
  eliminates a class of supply-chain-attack paths that Electron leaves
  open.

## Consequences
- **Rust in the client codebase.** The backend team is Python-first;
  desktop-agent maintenance requires either cross-training or a dedicated
  client engineer. Tracked.
- **Platform capture backends still to be written** — Tauri gets us the
  shell and the tray, but `NSWorkspace` / `SetWinEventHook` capture code
  is ours to write. Scaffold ships a heartbeat only (see
  `clients/desktop-agent/README.md` TODOs).
- **Auto-update infra.** Tauri's updater is solid but needs a code-signed
  release artefact server. Added to the infra roadmap.
- **Linux is deferred.** macOS + Windows covers >98% of customer laptops
  in our target ICP; Linux support is a later ADR.

## Alternatives and why they were rejected
- *Electron* — footprint, endpoint-protection friction.
- *Pure Go + systray* — no transparency UI, fails works-council requirement.
- *Native per-OS* — double engineering cost for little product gain.

## References
- Business Plan v4.5 §4.1.1 (Watch layer), §11A.5 (privacy-by-design),
  §14 (compliance scope).
- [clients/desktop-agent/README.md](../../clients/desktop-agent/README.md)
- [docs/security/employee-privacy-notice.md](../security/employee-privacy-notice.md)
