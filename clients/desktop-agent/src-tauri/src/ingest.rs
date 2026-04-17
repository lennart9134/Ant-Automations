// HTTP ingest client for the desktop agent.
//
// Posts batches of observation events to services/observation-ingest at
// `POST /api/v1/events/batch`. Fails soft — a missing ingest service must never crash the agent
// or cause event pile-up on the employee's machine.

use crate::events::ObservationEvent;
use anyhow::Result;
use serde::Serialize;

const DEFAULT_INGEST_URL: &str = "http://localhost:8006";
const BATCH_ENDPOINT: &str = "/api/v1/events/batch";

pub struct IngestClient {
    http: reqwest::Client,
    base_url: String,
}

#[derive(Serialize)]
struct EventBatch<'a> {
    events: &'a [ObservationEvent],
}

impl IngestClient {
    pub fn from_env() -> Self {
        let base_url =
            std::env::var("ANT_INGEST_URL").unwrap_or_else(|_| DEFAULT_INGEST_URL.to_string());
        Self {
            http: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(5))
                .build()
                .expect("reqwest client"),
            base_url,
        }
    }

    pub async fn publish(&self, events: &[ObservationEvent]) -> Result<()> {
        let url = format!("{}{}", self.base_url, BATCH_ENDPOINT);
        let body = EventBatch { events };
        let res = self.http.post(url).json(&body).send().await?;
        if !res.status().is_success() {
            anyhow::bail!(
                "ingest responded with {}: {}",
                res.status(),
                res.text().await.unwrap_or_default()
            );
        }
        Ok(())
    }
}
