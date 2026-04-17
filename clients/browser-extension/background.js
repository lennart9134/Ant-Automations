// Ant Observation Agent — MV3 service worker.
//
// Responsibilities:
//   1. Maintain pause/active state (persisted in chrome.storage.local so it
//      survives the service worker going to sleep).
//   2. Emit a heartbeat every HEARTBEAT_INTERVAL_MIN minutes via chrome.alarms.
//      (chrome.alarms is used instead of setInterval because MV3 service
//      workers are not persistent — setInterval would be killed at worker
//      shutdown.)
//   3. Listen for webNavigation commits and forward *path-template* events
//      (UUIDs / numeric IDs redacted) to the ingest service.
//   4. Receive form-submission *names* from the content script and forward
//      them. Field VALUES must never reach this service worker.
//
// NEVER add code that reads DOM text, clipboard, cookies, or auth headers.
// See clients/browser-extension/README.md for the full banned list.

import { emitEvent } from "./ingest.js";

const HEARTBEAT_INTERVAL_MIN = 0.5; // 30 seconds
const HEARTBEAT_ALARM = "ant-heartbeat";
const PAUSE_KEY = "ant.paused";

// Redact path segments that look like identifiers. Everything else passes
// through so the resulting path-template (e.g. "/orders/:id/invoice") is
// useful as a pattern-classifier signal.
const ID_PATTERNS = [
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, // UUID
  /^\d{4,}$/,                                                         // long number
  /^[A-Za-z0-9_-]{20,}$/,                                             // long opaque token
];

function redactPath(rawPath) {
  return rawPath
    .split("/")
    .map((seg) => (ID_PATTERNS.some((re) => re.test(seg)) ? ":id" : seg))
    .join("/");
}

async function isPaused() {
  const { [PAUSE_KEY]: paused } = await chrome.storage.local.get(PAUSE_KEY);
  return Boolean(paused);
}

async function loadManagedPolicy() {
  // chrome.storage.managed is set by the enterprise admin; returns {} when
  // the extension is loaded unpacked for development.
  const policy = await chrome.storage.managed.get([
    "tenantId",
    "ingestUrl",
    "scope",
    "hostAllowlist",
  ]);
  return policy;
}

async function hostInScope(hostname, policy) {
  if (!policy.hostAllowlist || policy.hostAllowlist.length === 0) {
    return false;
  }
  return policy.hostAllowlist.some((allowed) => {
    try {
      const u = new URL(allowed);
      return u.hostname === hostname;
    } catch {
      return false;
    }
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(HEARTBEAT_ALARM, {
    periodInMinutes: HEARTBEAT_INTERVAL_MIN,
  });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(HEARTBEAT_ALARM, {
    periodInMinutes: HEARTBEAT_INTERVAL_MIN,
  });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== HEARTBEAT_ALARM) return;
  if (await isPaused()) return;
  const policy = await loadManagedPolicy();
  await emitEvent(
    {
      action_type: "agent.heartbeat",
      source_application: "ant-browser-extension",
      target_application: "",
      duration_ms: 0,
      capture_channel: "browser",
      metadata: {},
    },
    policy,
  );
});

chrome.webNavigation.onCommitted.addListener(async (details) => {
  if (details.frameId !== 0) return; // top frame only
  if (await isPaused()) return;
  const policy = await loadManagedPolicy();
  let url;
  try {
    url = new URL(details.url);
  } catch {
    return;
  }
  if (!(await hostInScope(url.hostname, policy))) return;
  await emitEvent(
    {
      action_type: "browser.nav",
      source_application: "",
      target_application: url.hostname,
      duration_ms: 0,
      capture_channel: "browser",
      metadata: {
        path_template: redactPath(url.pathname),
        transition: details.transitionType,
      },
    },
    policy,
  );
});

// The content script forwards form-submission NAMES only (never values).
// We revalidate here — a compromised content script must not be able to
// widen the schema post-hoc.
chrome.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg?.type !== "ant.form.submit") return;
  if (await isPaused()) return;
  const policy = await loadManagedPolicy();
  const host = sender?.tab?.url ? new URL(sender.tab.url).hostname : "";
  if (!host || !(await hostInScope(host, policy))) return;

  const safeFieldNames = Array.isArray(msg.fieldNames)
    ? msg.fieldNames.filter((n) => typeof n === "string" && n.length < 128)
    : [];

  await emitEvent(
    {
      action_type: "browser.form_submit",
      source_application: "",
      target_application: host,
      duration_ms: 0,
      capture_channel: "browser",
      metadata: {
        form_name: typeof msg.formName === "string" ? msg.formName : "",
        field_names: safeFieldNames,
      },
    },
    policy,
  );
});
