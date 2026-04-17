# Ant Observation Browser Extension (Chrome MV3)

Browser-side observation capture for the Watch layer of the Ant platform. Ships
as a Chrome Manifest V3 extension; the same codebase will be adapted for Edge
and Firefox later.

## Scope (what it captures)

- **Tab/navigation events** — SaaS host + path template only (path segments
  that match UUIDs, numeric IDs, or look like tokens are redacted).
- **Form submission *names*** — the `name=` / `id=` attributes of submitted
  forms and their field names. **Never the values**.
- **Click targets by role** — button labels and link destinations at the host
  level. Never the surrounding DOM content.
- **Heartbeat** — one event every 30 s so the operator can see the extension
  is alive.

## Scope (what it NEVER captures — enforced in code)

- Keystrokes or key events beyond form-submission boundaries.
- Form *values* of any kind (including passwords, emails, messages, free text).
- Clipboard contents.
- Screen contents, DOM snapshots, innerText of elements.
- Cookies, localStorage, IndexedDB contents, session tokens, bearer headers.

This list mirrors [services/observation-ingest/src/privacy.py](../../services/observation-ingest/src/privacy.py).
The ingest service will reject any payload that carries a banned key, so a
capture bug in the extension becomes a loud server-side failure rather than
a silent privacy incident.

## Why Manifest V3 (and not a content script shim)

- Chrome deprecates MV2 (persistent background pages) in 2024. Building new on
  MV2 would ship dead-on-arrival.
- Service-worker background model forces us to keep state in `chrome.storage`
  rather than long-lived in-memory caches — which happens to be what we want
  for a low-footprint observation tool.
- `host_permissions` is per-origin, letting the customer allowlist exactly
  which SaaS apps are in-scope, per ADR [007](../../docs/adr/007-chrome-mv3-extension.md).

## Current state

This is a scaffold. Today the extension:

- Declares MV3 manifest with narrow permissions (`activeTab`, `webNavigation`,
  `storage`, `alarms`).
- Emits a heartbeat every 30 s via `chrome.alarms`.
- Listens to `chrome.webNavigation.onCommitted` for SaaS host/path-template
  events.
- Forwards form-submission names (never values) via a content script.
- Shows a popup explaining what is captured and offering a "pause" toggle.
- Persists pause state in `chrome.storage.local`.

What is NOT yet wired:

- Enterprise policy JSON (`managed_schema`) for fleet-wide allowlist + force-on.
- CWS signing / enterprise publisher setup.
- `chrome.identity` device-bound token flow (today's build reads a bearer
  token from `chrome.storage.local` for development only).

See the `TODO` comments in `background.js` for the exact next steps.

## Install (development)

```
# 1. Build (no build step required for the scaffold; pure JS)
# 2. Chrome → Extensions → Developer mode → Load unpacked
# 3. Point at clients/browser-extension/
```

For production the extension will be distributed via:
- Chrome Web Store (unlisted) for individual installs.
- Google Admin / `ExtensionInstallForcelist` policy for fleet rollouts.

## Compliance

The extension is in-scope for the same controls as the desktop agent:
- [DPIA: observation layer](../../docs/security/dpia-observation-layer.md)
- [Employee privacy notice](../../docs/security/employee-privacy-notice.md)
- [Betriebsvereinbarung template (DE)](../../docs/security/betriebsvereinbarung-template.md)
- [Instemmingsverzoek template (NL)](../../docs/security/instemmingsverzoek-template.md)

Do **not** widen the permissions in `manifest.json` without first amending
these documents. MV3 `host_permissions` expansions are reviewed both by
Chrome Web Store *and* by the customer's works council — a silent widening
will be caught, painfully.
