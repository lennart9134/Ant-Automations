// Wire-schema event types for the desktop agent.
//
// This struct MUST match the shape accepted by services/observation-ingest
// (see services/observation-ingest/src/main.rs::ObservationEvent). If you change one you
// must change the other in the same commit.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use tauri::AppHandle;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CaptureChannel {
    Desktop,
    Browser,
    ApiTap,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObservationEvent {
    pub tenant_id: String,
    pub actor_id: String,
    pub timestamp: DateTime<Utc>,
    pub action_type: String,
    #[serde(default)]
    pub source_application: String,
    #[serde(default)]
    pub target_application: String,
    #[serde(default)]
    pub duration_ms: u64,
    pub capture_channel: CaptureChannel,
    /// Metadata must contain field NAMES and action kinds only — never user content.
    /// The ingest service will reject any payload that carries banned keys.
    #[serde(default)]
    pub metadata: BTreeMap<String, serde_json::Value>,
}

/// Produce a heartbeat event. Used until platform capture backends are wired up.
pub fn heartbeat_event(_app: &AppHandle) -> ObservationEvent {
    let tenant_id = std::env::var("ANT_TENANT_ID").unwrap_or_else(|_| "dev-tenant".to_string());
    let actor_id = std::env::var("ANT_ACTOR_ID").unwrap_or_else(|_| "dev-actor".to_string());
    ObservationEvent {
        tenant_id,
        actor_id,
        timestamp: Utc::now(),
        action_type: "agent.heartbeat".to_string(),
        source_application: "ant-desktop-agent".to_string(),
        target_application: String::new(),
        duration_ms: 0,
        capture_channel: CaptureChannel::Desktop,
        metadata: BTreeMap::new(),
    }
}
