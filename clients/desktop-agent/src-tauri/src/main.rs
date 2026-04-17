// Ant Automations desktop observation agent (Tauri).
//
// This is the scaffold. What exists today:
//   - A configured system tray.
//   - A heartbeat event emitted on an interval (so ingest wiring can be end-to-end tested).
//   - An `ObservationEvent` struct that matches the ingest wire schema byte-for-byte.
//
// What is deliberately missing:
//   - Platform-specific capture (NSWorkspace on macOS, SetWinEventHook on Windows, etc.).
//   - A tray menu with a working pause toggle.
//   - A signed release build pipeline.
//
// These are tracked in clients/desktop-agent/README.md ("Next-step TODOs"). Do NOT widen the
// capture scope beyond the metadata categories listed in
// docs/security/employee-privacy-notice.md — if you need to, amend the notice, the DPIA, and
// the Betriebsvereinbarung first.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod events;
mod ingest;

use std::time::Duration;
use tauri::{Manager, RunEvent};

const HEARTBEAT_INTERVAL_SECS: u64 = 30;

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter("info,ant_desktop_agent=debug")
        .init();

    let builder = tauri::Builder::default().setup(|app| {
        let handle = app.handle().clone();

        // Start the heartbeat task. Each heartbeat is a synthetic observation event that proves
        // the ingest path is reachable. Real capture backends will replace this with actual
        // application-switch, focus, and file-event captures.
        tauri::async_runtime::spawn(async move {
            let client = ingest::IngestClient::from_env();
            let mut ticker = tokio::time::interval(Duration::from_secs(HEARTBEAT_INTERVAL_SECS));
            loop {
                ticker.tick().await;
                let event = events::heartbeat_event(&handle);
                if let Err(err) = client.publish(&[event]).await {
                    tracing::warn!(?err, "heartbeat publish failed — agent will keep retrying");
                }
            }
        });

        Ok(())
    });

    builder
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                // Keep the agent alive when the main window is closed; it is a background service.
                api.prevent_exit();
            }
        });
}
