# ADR 007: Chrome Manifest V3 for the browser observation agent

## Status
Accepted

## Context
The Watch layer must capture SaaS workflow metadata that the desktop agent
can't see: browser-level navigation (path templates, transition types) and
form-submission field names. SaaS work increasingly happens inside a single
browser tab, so a desktop-only agent would leave a large blind spot.

Constraints:

- Must respect the same privacy denylist as the desktop agent (no form
  *values*, no clipboard, no cookies, no screenshots).
- Must be deployable via Google Admin / `ExtensionInstallForcelist` for
  fleet-wide installs, or via Chrome Web Store for smaller customers.
- Must survive Chrome's deprecation of persistent background pages (MV2
  retirement).
- Must support per-tenant host allowlists so a customer can scope
  observation to exactly the SaaS apps they have DPAs with.

Options considered:

1. **Chrome Manifest V3 extension.** Standard, enterprise-deployable,
   MV2 is being retired in 2024/2025.
2. **Firefox WebExtension.** Still supports MV2 + MV3; customer browser
   share is <5% in target ICP.
3. **Browser-agnostic page-hosted agent** (inject a script tag per SaaS
   tenant). Requires per-SaaS integration work and can't enforce the
   denylist client-side.

## Decision
Ship a **Chrome Manifest V3** extension as the primary browser observation
surface. Chromium-based Edge is supported automatically (same extension
package). Firefox and Safari are deferred.

## Rationale
- **Enterprise deployment is a solved problem** on Chrome via
  `ExtensionInstallForcelist` and `managed_schema.json`. The extension
  ships with a managed policy schema describing `tenantId`, `ingestUrl`,
  `hostAllowlist`, and `pauseAllowed` so the customer's Google Admin or
  MDM can configure the fleet centrally and prevent tampering.
- **MV3 is the only supportable future.** Chrome is removing MV2 support.
  Building on MV3 from day one avoids a second migration.
- **Service-worker constraints match our design.** MV3 doesn't allow
  persistent background pages. That's fine — our background logic is
  event-driven (nav events, form submits, alarms) and keeps no long-lived
  in-memory state. `chrome.alarms` replaces `setInterval`; `chrome.storage`
  replaces globals.
- **`host_permissions` maps cleanly to the Betriebsvereinbarung scope.**
  Every SaaS origin the extension can see is explicitly allowlisted per
  tenant. Expanding the allowlist requires re-running works-council
  approval, which is exactly what §9 of the Betriebsvereinbarung template
  demands.
- **Content-script surface is small and auditable.** The content script
  is ~20 lines and does one thing: forward form field *names* on submit.
  A reviewer can verify the invariant (no values, no DOM text) at a
  glance — deliberate design choice.

## Consequences
- **Firefox + Safari are later work.** Chromium + Chromium-Edge covers
  the vast majority of enterprise deployments. Firefox MV3 differs
  slightly; Safari needs a separate app-store flow.
- **Enterprise publisher account required** for Chrome Web Store
  (unlisted + force-install). Added to infra roadmap.
- **Service-worker lifecycle discipline.** Because the worker can be
  shut down between events, any state must be persisted to
  `chrome.storage`. Team convention: never use module-level `let` for
  state in `background.js`.
- **Optional host permissions** are used for the scoped allowlist, so
  Chrome presents the user with a per-origin permission prompt if the
  tenant adds a new SaaS. This is a feature, not a bug — it echoes the
  works-council transparency requirement.

## Alternatives and why they were rejected
- *Firefox-first* — install base in target ICP too small to justify
  diverging from the MV3 mainline.
- *Page-injected scripts per SaaS* — O(n) SaaS-specific integration work
  and far weaker privacy guarantees (the script runs in page context with
  full DOM access).

## References
- Business Plan v4.5 §4.1.1, §11A.5, §14.
- [clients/browser-extension/manifest.json](../../clients/browser-extension/manifest.json)
- [clients/browser-extension/managed_schema.json](../../clients/browser-extension/managed_schema.json)
- ADR [006](006-tauri-desktop-agent.md) (desktop counterpart)
