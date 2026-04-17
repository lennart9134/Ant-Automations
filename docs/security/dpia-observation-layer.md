# Data Protection Impact Assessment — Observation layer

> **Status:** template. To be completed by the **customer** (the
> controller) for each deployment. Ant Automations (the processor) supplies
> the technical sections marked "Processor-supplied". The rest must be
> filled in per-customer.
>
> **Legal basis:** GDPR Art. 35 (DPIA required where processing is likely
> to result in a high risk); EDPB WP248 rev.01 guidelines; for EU AI Act
> purposes, the Watch layer is a **high-risk system** (Annex III §4 —
> employment) and this DPIA doubles as the Fundamental Rights Impact
> Assessment.

## 1. Metadata

| Field | Value |
| --- | --- |
| Controller | _[customer legal entity]_ |
| Processor | Ant Automations B.V. |
| DPIA version | 1.0 (template) |
| Date | _[fill at sign-off]_ |
| Review cadence | Annually, and when observation scope changes |
| Works council consulted | Yes / No — _[date of consultation]_ |

## 2. Description of processing *(Processor-supplied)*

The Ant Observation Agent captures **metadata** about employee interaction
with work software. It runs as:

- A Tauri desktop application on macOS and Windows (tray-resident).
- A Chrome Manifest V3 browser extension (host-allowlisted).

Captured categories, with the exhaustive list of fields:

| Category | Fields captured |
| --- | --- |
| `desktop.window_focus` | `target_application`, `duration_ms` |
| `desktop.app_switch` | `source_application`, `target_application` |
| `desktop.file_event` | `target_application`, `metadata.filename`, `metadata.action` (`open`/`save`/`close`) |
| `browser.nav` | `target_application` (hostname), `metadata.path_template` (redacted), `metadata.transition` |
| `browser.form_submit` | `target_application`, `metadata.form_name`, `metadata.field_names[]` |
| `agent.heartbeat` | none beyond actor + tenant |

**Explicitly NOT captured** (enforced in code at
`services/observation-ingest/src/privacy.py::CONTENT_FIELD_DENYLIST`):

- Keystrokes.
- Clipboard contents.
- Form-field *values* of any kind.
- Screenshots, screen recordings, or DOM snapshots.
- File contents.
- Cookies, bearer tokens, authorization headers, session identifiers.

The ingest service rejects events containing any of these field names;
rejected events raise a P1 alert to the security team.

## 3. Purpose and necessity

**Purpose:** to detect repetitive multi-step workflows performed by
**three or more** employees, so that each such workflow can be proposed to
the workforce for automation.

**Necessity test:**

- The purpose cannot be achieved through interview-based process discovery
  alone — multi-step patterns spanning 5–20 UI actions are not reliably
  recalled in interviews.
- Lighter-weight alternatives (e.g. self-reporting, task diaries) were
  considered and rejected as both higher-effort for employees and
  lower-accuracy.
- The minimum-three-employee aggregation gate (see §6) is the minimum
  sufficient constraint to prevent individual profiling.

## 4. Lawful basis

Fill in one of:

- [ ] **Art. 6(1)(f) legitimate interest**, with the balancing test in
  §4.1 of this document.
- [ ] **Works agreement (Germany: Betriebsvereinbarung under BetrVG
  §87(1) Nr. 6; Netherlands: instemming under WOR Art. 27(1)(l))**,
  reference: _[filed copy]_.
- [ ] **Art. 6(1)(b) contractual necessity**, narrowly scoped to _[role]_.

### 4.1 Balancing test (Art. 6(1)(f))

_[Controller to complete: interest of controller × necessity × employee
rights and reasonable expectations. Must explicitly consider that
employees are in a subordinate relationship and that consent is generally
not a valid basis.]_

## 5. Risk assessment

| Risk | Likelihood | Severity | Mitigation |
| --- | --- | --- | --- |
| Re-identification via metadata correlation | Medium | High | Min-3-employee aggregation gate (code-enforced); raw data only visible to DPO with ticket |
| Scope creep (capturing more than declared) | Medium | High | Field denylist in ingest service rejects unknown content fields; quarterly audit vs. declared scope |
| Secondary use (e.g. for performance reviews) | Low | High | Contractual prohibition in DPA §3.2; separation of duties (HR cannot query observation store) |
| Data breach of observation store | Low | Medium | Row-level security per tenant; 90-day raw retention limits blast radius |
| Chilling effect on employees | Medium | Medium | Transparency (privacy notice, pause toggle), works council co-determination, published retention |
| Proposal system used to intensify workload | Low | High | Works council approval required per proposal; proposals only, never auto-executed |
| EU AI Act Annex III (employment) non-compliance | Low | High | Human review required before any proposal reaches an employee; audit trail in `proposal_decisions` table |

## 6. Technical & organisational measures

**Processor-supplied (documented in code):**

1. **Field denylist** — services/observation-ingest/src/privacy.py enforces
   that no banned content field can reach storage.
2. **Min-3 aggregation gate** — `services/pattern-classifier/src/constraints.py::MIN_EMPLOYEE_AGGREGATION = 3`
   is a module-level constant with a unit test asserting the value. Patterns
   with fewer contributors are dropped before reaching the proposal queue.
3. **Split retention** — `observation_retention_raw_days` (default 90) and
   `observation_retention_aggregated_days` (default 365) are distinct tenant
   columns with a DB-level CHECK.
4. **Schema isolation** — observation tables live in a separate Postgres
   `observation` schema, so a misconfigured query in the execution services
   cannot accidentally read raw observation data.
5. **Row-level security** — tenant isolation enforced at the DB layer.
6. **Audit trail** — every proposal approval, rejection, or modification is
   recorded in `proposal_decisions`.

**Controller-supplied:**

- _[SSO / identity provider configuration]_
- _[Access controls for DPO and data-subject-request workflow]_
- _[Incident response plan integration]_
- _[Employee privacy notice distributed via: …]_

## 7. Consultation

- **Works council** — _[date, outcome]_
- **Employees** — _[survey results if performed]_
- **DPO** — _[sign-off]_
- **Supervisory authority (if required by national law)** — _[N/A unless
  high residual risk after mitigation]_

## 8. Decision

- [ ] Proceed — residual risk acceptable.
- [ ] Proceed with conditions: _[list]_
- [ ] Do not proceed.

Signed: _[controller DPO]_, _[date]_
