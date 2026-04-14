-- Ant Automations Demo Seed Data
-- Run against a fresh 'ant' database after Alembic migrations.

BEGIN;

-- ============================================================
-- 1. Tenants
-- ============================================================

INSERT INTO tenants (tenant_id, name, domain, workflow_templates, connector_configs, approval_policies, feature_flags, data_residency, retention_days)
VALUES
  ('acme-corp', 'ACME Corporation', 'acme-corp.example.com',
   '{"access_provisioning": {"enabled": true}, "ticket_triage": {"enabled": true}}',
   '{"entra_id": {"tenant_id": "demo-entra-tenant"}, "servicenow": {"instance": "demo-snow"}}',
   '{"default_mode": "supervised", "high_risk_escalation": "security-team-lead@acme-corp.example.com"}',
   '{"shadow_mode": true, "autonomous_low_risk": false}',
   'eu-west-1', 90),

  ('globex-gmbh', 'Globex GmbH', 'globex.example.de',
   '{"access_provisioning": {"enabled": true}, "ticket_triage": {"enabled": false}}',
   '{"entra_id": {"tenant_id": "demo-globex-tenant"}}',
   '{"default_mode": "observation", "high_risk_escalation": "it-lead@globex.example.de"}',
   '{"shadow_mode": true, "autonomous_low_risk": false}',
   'eu-central-1', 180);


-- ============================================================
-- 2. Approval Requests (pre-populated demo scenarios)
-- ============================================================

-- Scenario A: Joiner — new engineer at ACME, awaiting manager approval
INSERT INTO approval_requests (id, correlation_id, workflow_run_id, action_description, risk_level, state, timeout_seconds, escalation_target, created_at)
VALUES
  ('a0000001-0000-0000-0000-000000000001', 'demo-joiner-001', 'wf-run-demo-001',
   'Create Entra ID account and assign engineering groups for jane.doe@acme-corp.example.com',
   'medium', 'pending', 3600, 'eng-manager@acme-corp.example.com', NOW() - INTERVAL '5 minutes');

INSERT INTO approval_steps (request_id, approver_id, required, decided, decision)
VALUES
  ('a0000001-0000-0000-0000-000000000001', 'eng-manager@acme-corp.example.com', true, false, 'pending'),
  ('a0000001-0000-0000-0000-000000000001', 'it-admin@acme-corp.example.com', true, false, 'pending');

-- Scenario B: Leaver — high-risk account disable, already approved
INSERT INTO approval_requests (id, correlation_id, workflow_run_id, action_description, risk_level, state, timeout_seconds, created_at, resolved_at)
VALUES
  ('a0000002-0000-0000-0000-000000000002', 'demo-leaver-001', 'wf-run-demo-002',
   'Disable account and revoke all sessions for departing employee bob.smith@acme-corp.example.com',
   'high', 'approved', 3600, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour');

INSERT INTO approval_steps (request_id, approver_id, required, decided, decision, decided_at, comment)
VALUES
  ('a0000002-0000-0000-0000-000000000002', 'security-team-lead@acme-corp.example.com', true, true, 'approved', NOW() - INTERVAL '1 hour', 'Verified with HR — last day confirmed.'),
  ('a0000002-0000-0000-0000-000000000002', 'it-admin@acme-corp.example.com', true, true, 'approved', NOW() - INTERVAL '90 minutes', 'Approved — backup of mailbox scheduled.');


-- ============================================================
-- 3. Audit Events (recent activity for dashboards)
-- ============================================================

INSERT INTO audit_events (id, timestamp, event_type, correlation_id, tenant_id, actor, resource, action, details, risk_level, outcome)
VALUES
  -- Joiner workflow events
  (gen_random_uuid(), NOW() - INTERVAL '10 minutes', 'workflow.started', 'demo-joiner-001', 'acme-corp',
   'planner-service', 'access_provisioning', 'workflow.start',
   '{"event_type": "joiner", "user_email": "jane.doe@acme-corp.example.com", "department": "engineering"}',
   'medium', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '9 minutes', 'actions.planned', 'demo-joiner-001', 'acme-corp',
   'planner-service', 'access_provisioning', 'plan_actions',
   '{"planned_count": 10, "actions": ["create_user", "assign_group x4", "provision_app_access x5"]}',
   'medium', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '8 minutes', 'approval.requested', 'demo-joiner-001', 'acme-corp',
   'control-plane', 'approval_requests', 'create',
   '{"approvers": ["eng-manager@acme-corp.example.com", "it-admin@acme-corp.example.com"]}',
   'medium', 'success'),

  -- Leaver workflow events
  (gen_random_uuid(), NOW() - INTERVAL '3 hours', 'workflow.started', 'demo-leaver-001', 'acme-corp',
   'planner-service', 'access_provisioning', 'workflow.start',
   '{"event_type": "leaver", "user_email": "bob.smith@acme-corp.example.com", "department": "sales"}',
   'high', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '2 hours 55 minutes', 'actions.planned', 'demo-leaver-001', 'acme-corp',
   'planner-service', 'access_provisioning', 'plan_actions',
   '{"planned_count": 5, "actions": ["disable_account", "revoke_all_sessions", "remove_group x3"]}',
   'high', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '1 hour', 'approval.decided', 'demo-leaver-001', 'acme-corp',
   'security-team-lead@acme-corp.example.com', 'approval_requests', 'approve',
   '{"decision": "approved", "comment": "Verified with HR"}',
   'high', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '55 minutes', 'connector.executed', 'demo-leaver-001', 'acme-corp',
   'entra-id-connector', 'bob.smith@acme-corp.example.com', 'disable_account',
   '{"connector": "entra_id", "ms_graph_response": 204}',
   'high', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '54 minutes', 'connector.executed', 'demo-leaver-001', 'acme-corp',
   'entra-id-connector', 'bob.smith@acme-corp.example.com', 'revoke_all_sessions',
   '{"connector": "entra_id", "ms_graph_response": 204}',
   'high', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '50 minutes', 'workflow.completed', 'demo-leaver-001', 'acme-corp',
   'planner-service', 'access_provisioning', 'workflow.complete',
   '{"verification": "all_actions_verified", "duration_seconds": 7200}',
   'high', 'success'),

  -- Ticket triage events
  (gen_random_uuid(), NOW() - INTERVAL '30 minutes', 'workflow.started', 'demo-triage-001', 'acme-corp',
   'planner-service', 'ticket_triage', 'workflow.start',
   '{"ticket_id": "INC0012345", "title": "VPN gateway down for EMEA office"}',
   'low', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '29 minutes', 'workflow.completed', 'demo-triage-001', 'acme-corp',
   'planner-service', 'ticket_triage', 'workflow.complete',
   '{"category": "infrastructure", "priority": "critical", "assigned_team": "infra-ops", "sla_hours": 1}',
   'low', 'success'),

  -- Shadow mode / observation events for Globex
  (gen_random_uuid(), NOW() - INTERVAL '45 minutes', 'workflow.started', 'demo-shadow-001', 'globex-gmbh',
   'planner-service', 'access_provisioning', 'workflow.start',
   '{"event_type": "joiner", "user_email": "anna.mueller@globex.example.de", "department": "finance", "mode": "observation"}',
   'low', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '44 minutes', 'actions.planned', 'demo-shadow-001', 'globex-gmbh',
   'planner-service', 'access_provisioning', 'plan_actions',
   '{"planned_count": 8, "mode": "observation", "note": "Actions logged but NOT executed — shadow mode active"}',
   'low', 'success'),

  (gen_random_uuid(), NOW() - INTERVAL '43 minutes', 'workflow.completed', 'demo-shadow-001', 'globex-gmbh',
   'planner-service', 'access_provisioning', 'workflow.complete',
   '{"mode": "observation", "side_effects": 0, "planned_actions_logged": 8}',
   'low', 'success');

COMMIT;
