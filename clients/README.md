# clients/

Employee-facing clients for the Watch layer of the Ant Automations platform.

| Path | Runtime | Deployment target |
|---|---|---|
| `desktop-agent/` | Tauri (Rust + WebView) | Employee laptops — macOS, Windows, Linux |
| `browser-extension/` | Chrome Extension Manifest V3 | Chrome / Edge on employee machines |

Both clients emit events to `services/observation-ingest` using the canonical wire schema
documented in [`services/observation-ingest/README.md`](../services/observation-ingest/README.md).
Neither client captures user content — see [`docs/adr/006`](../docs/adr/006-tauri-desktop-agent.md)
and [`docs/adr/007`](../docs/adr/007-chrome-mv3-extension.md).

## Why two clients

- **Desktop agent** sees application-level events (process switches, focus changes, file
  open/save) that a browser extension cannot see.
- **Browser extension** sees web-workflow events (URL navigation within an allowlisted domain,
  form-submission events by field name, tab switches) with much lower install friction than an
  OS agent.

Many customers start with the browser extension alone — it deploys through existing Chrome
enterprise MDM/GPO policy with zero OS-level footprint. The desktop agent is offered once the
customer is comfortable.

## Privacy invariant

Both clients run under the same invariant: **capture patterns, not content.** The ingest service
enforces this with a denylist of banned field names
([`services/observation-ingest/src/privacy.py`](../services/observation-ingest/src/privacy.py)).
Any payload that contains a banned key is rejected at the ingest boundary. This is deliberate
defence-in-depth; the clients themselves must also avoid capturing content in the first place.
