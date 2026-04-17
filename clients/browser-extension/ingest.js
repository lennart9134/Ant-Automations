// HTTP ingest client for the browser extension.
//
// Mirrors the wire schema of services/observation-ingest. If you change the
// schema you must update this file AND clients/desktop-agent/src-tauri/src/events.rs
// AND services/observation-ingest/src/main.rs — in the same PR.
//
// This module is deliberately tiny. Everything that could be considered
// policy (what to capture, when to pause, which hosts are in-scope) lives in
// background.js so the same ingest client can be reused in tests.

const BATCH_ENDPOINT = "/api/v1/events/batch";

function nowIso() {
  return new Date().toISOString();
}

/** Build a fully-formed ObservationEvent from a partial shape. */
function buildEvent(partial, policy, identity) {
  return {
    tenant_id: policy.tenantId ?? "dev-tenant",
    actor_id: identity.actorId ?? "dev-actor",
    timestamp: nowIso(),
    action_type: partial.action_type,
    source_application: partial.source_application ?? "",
    target_application: partial.target_application ?? "",
    duration_ms: partial.duration_ms ?? 0,
    capture_channel: partial.capture_channel ?? "browser",
    metadata: partial.metadata ?? {},
  };
}

async function loadIdentity() {
  // TODO: replace with chrome.identity device-bound flow once the ingest
  // service supports it (tracked in ADR 007). For dev we read a preseeded
  // actor id from local storage.
  const { "ant.actorId": actorId } = await chrome.storage.local.get("ant.actorId");
  return { actorId: actorId ?? "dev-actor" };
}

export async function emitEvent(partial, policy) {
  const ingestUrl = policy.ingestUrl ?? "http://localhost:8006";
  const identity = await loadIdentity();
  const event = buildEvent(partial, policy, identity);
  try {
    const res = await fetch(`${ingestUrl}${BATCH_ENDPOINT}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ events: [event] }),
      // Observation is best-effort; never block the browser if ingest is down.
      keepalive: true,
    });
    if (!res.ok) {
      console.warn("[ant] ingest responded non-2xx", res.status);
    }
  } catch (err) {
    console.warn("[ant] ingest publish failed", err);
  }
}
