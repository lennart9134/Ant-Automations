"""Observation & discovery schema — Watch / Learn / Propose.

Revision ID: 002
Revises: 001
Create Date: 2026-04-17

Business Plan v4.5 alignment
============================
This migration lands the data model for the three v4.5 layers that were missing from 001:

- Watch   → observation.observation_events  (raw interaction events from desktop/browser/API)
- Learn   → observation.observed_sequences  (sliding-window sequences mined from events)
            observation.workflow_candidates (HDBSCAN clusters of similar sequences)
- Propose → observation.proposals           (team-lead-facing automation proposals)
            observation.proposal_decisions  (accept / reject / defer decisions)

Everything related to observation data lives in a dedicated `observation` schema, not `public`.
This is required by v4.5 §14 ("observation event store in isolated database partition with separate
access controls") and by the works-council agreements we ship to DACH customers.

Retention split
---------------
v4.4 `tenants.retention_days` was a single value covering everything. v4.5 requires different
retention for:

- Raw observation events         → default 90 days  (observation_retention_raw_days)
- Aggregated observation data    → default 365 days (observation_retention_aggregated_days)
- Audit / workflow / approval    → existing behaviour via audit_retention_days (was retention_days)

See docs/adr/009-observation-data-retention.md and §11A.5 of the business plan.

Employee aggregation gate (§11A.5)
----------------------------------
The rule that a pattern must be seen in ≥3 distinct employees before it can be surfaced is
enforced in the pattern-classifier service, not in SQL. The schema supports it by storing
`employee_count` on `workflow_candidates` and CHECK-constraining `proposals` to rows that meet
the threshold. The value of the threshold lives in one place:
services/pattern-classifier/src/constraints.py::MIN_EMPLOYEE_AGGREGATION.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Isolated schema for observation data
    # ------------------------------------------------------------------
    # Observation data has a different access model than audit/workflow data.
    # Keeping it in its own Postgres schema makes GRANT/REVOKE straightforward and
    # matches the separation promised in the works-council Betriebsvereinbarung.
    op.execute("CREATE SCHEMA IF NOT EXISTS observation")

    # ------------------------------------------------------------------
    # 2. tenants — split retention columns
    # ------------------------------------------------------------------
    # v4.4 shipped a single retention_days column. v4.5 requires three values.
    # We keep the old column (renamed) so existing rows aren't lost, and add the
    # two new observation-specific retention columns.
    op.alter_column(
        "tenants", "retention_days", new_column_name="audit_retention_days"
    )
    op.add_column(
        "tenants",
        sa.Column(
            "observation_retention_raw_days",
            sa.Integer,
            server_default="90",
            nullable=False,
            comment="Retention in days for raw observation events. Default 90 per v4.5 §11A.5.",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "observation_retention_aggregated_days",
            sa.Integer,
            server_default="365",
            nullable=False,
            comment="Retention in days for aggregated observation data (candidates, proposals). "
            "Default 365 per v4.5 §11A.5.",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "observation_scope",
            sa.String(32),
            server_default="minimal",
            nullable=False,
            comment="'minimal' | 'application' | 'action' — see v4.5 §11A.5 product response #3.",
        ),
    )

    # ------------------------------------------------------------------
    # 3. observation.observation_events  (Step 1–2 of the 9-step loop)
    # ------------------------------------------------------------------
    op.create_table(
        "observation_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        # actor_id is a pseudonymous per-tenant identifier, NOT an email. Mapping from
        # actor_id to employee identity is held by the customer, not by us.
        sa.Column("actor_id", sa.String(128), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("source_application", sa.String(128), server_default=""),
        sa.Column("target_application", sa.String(128), server_default=""),
        sa.Column("duration_ms", sa.Integer, server_default="0"),
        # `metadata` is deliberately narrow — field NAMES and action kinds only, never values.
        # The schema validator in observation-ingest rejects any payload that looks like content
        # (clipboard text, form values, keystroke data, screenshots).
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "capture_channel",
            sa.String(16),
            nullable=False,
            comment="'desktop' | 'browser' | 'api_tap' — where this event came from.",
        ),
        schema="observation",
    )
    op.create_index(
        "ix_observation_events_tenant_actor_ts",
        "observation_events",
        ["tenant_id", "actor_id", "timestamp"],
        schema="observation",
    )

    # ------------------------------------------------------------------
    # 4. observation.observed_sequences  (Step 3 — sliding-window extraction)
    # ------------------------------------------------------------------
    op.create_table(
        "observed_sequences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("actor_id", sa.String(128), nullable=False, index=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "action_sequence",
            ARRAY(sa.String(128)),
            nullable=False,
            comment="Ordered list of action_type keys (no user content).",
        ),
        sa.Column("occurrences", sa.Integer, server_default="1", nullable=False),
        sa.Column("total_duration_ms", sa.BigInteger, server_default="0", nullable=False),
        # Embedding vector is stored in MinIO + a reference here to avoid pgvector at seed.
        sa.Column("embedding_ref", sa.String(512), nullable=True),
        schema="observation",
    )

    # ------------------------------------------------------------------
    # 5. observation.workflow_candidates  (Step 3–4 — HDBSCAN clusters)
    # ------------------------------------------------------------------
    op.create_table(
        "workflow_candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column("cluster_label", sa.Integer, nullable=False, index=True),
        sa.Column("pattern_description", sa.Text, server_default=""),
        sa.Column("occurrences_per_week", sa.Float, server_default="0"),
        sa.Column("avg_duration_ms", sa.Integer, server_default="0"),
        sa.Column("estimated_fte_hours_per_week", sa.Float, server_default="0"),
        sa.Column("estimated_annual_cost_eur", sa.Float, server_default="0"),
        sa.Column("feasibility_score", sa.Float, server_default="0"),
        sa.Column("confidence_score", sa.Float, server_default="0"),
        sa.Column(
            "employee_count",
            sa.Integer,
            nullable=False,
            comment="Number of distinct actor_ids the cluster was observed across. "
            "Must be >= MIN_EMPLOYEE_AGGREGATION (default 3) before it can promote to a proposal. "
            "See services/pattern-classifier/src/constraints.py.",
        ),
        sa.Column("first_observed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_sequence", ARRAY(sa.String(128)), nullable=True),
        # Soft link to the originating actor_ids as a hash list — never stored as raw IDs
        # once promoted to a proposal. Enforced by the pattern classifier contract.
        sa.Column("actor_id_hashes", ARRAY(sa.String(64)), nullable=True),
        schema="observation",
    )

    # ------------------------------------------------------------------
    # 6. observation.proposals  (Step 5 — team-lead-facing)
    # ------------------------------------------------------------------
    op.create_table(
        "proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "candidate_id",
            UUID(as_uuid=True),
            sa.ForeignKey("observation.workflow_candidates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column(
            "risk_level",
            sa.String(16),
            nullable=False,
            comment="'low' | 'medium' | 'high' — drives recommended execution mode.",
        ),
        sa.Column(
            "recommended_mode",
            sa.String(32),
            nullable=False,
            comment="'observation' | 'supervised' | 'autonomous' — advisory for the operator.",
        ),
        sa.Column("confidence_score", sa.Float, server_default="0"),
        sa.Column(
            "state",
            sa.String(16),
            nullable=False,
            server_default="pending",
            comment="'pending' | 'accepted' | 'rejected' | 'deferred'.",
        ),
        sa.Column(
            "employee_count",
            sa.Integer,
            nullable=False,
            comment="Carried over from the candidate. CHECK constraint enforces >= 3.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        # HARD GATE: a proposal that is not backed by ≥3 distinct employees violates v4.5 §11A.5.
        # The application enforces this at the classifier boundary; this CHECK is belt-and-braces.
        sa.CheckConstraint("employee_count >= 3", name="ck_proposals_min_employee_aggregation"),
        sa.CheckConstraint(
            "state IN ('pending', 'accepted', 'rejected', 'deferred')",
            name="ck_proposals_state",
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="ck_proposals_risk_level",
        ),
        sa.CheckConstraint(
            "recommended_mode IN ('observation', 'supervised', 'autonomous')",
            name="ck_proposals_recommended_mode",
        ),
        schema="observation",
    )
    op.create_index(
        "ix_proposals_tenant_state",
        "proposals",
        ["tenant_id", "state"],
        schema="observation",
    )

    # ------------------------------------------------------------------
    # 7. observation.proposal_decisions  (audit of accept/reject/defer)
    # ------------------------------------------------------------------
    # Note: this is a deliberately separate table from public.audit_events. Proposal decisions
    # are sensitive in a different way — they are about employee-adjacent work patterns. Mixing
    # them with infra audit events would complicate the retention and access split.
    op.create_table(
        "proposal_decisions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "proposal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("observation.proposals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("decided_by", sa.String(256), nullable=False),
        sa.Column(
            "decision",
            sa.String(16),
            nullable=False,
            comment="'accepted' | 'rejected' | 'deferred'.",
        ),
        sa.Column("comment", sa.Text, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('accepted', 'rejected', 'deferred')",
            name="ck_proposal_decisions_decision",
        ),
        schema="observation",
    )


def downgrade() -> None:
    op.drop_table("proposal_decisions", schema="observation")
    op.drop_index("ix_proposals_tenant_state", table_name="proposals", schema="observation")
    op.drop_table("proposals", schema="observation")
    op.drop_table("workflow_candidates", schema="observation")
    op.drop_table("observed_sequences", schema="observation")
    op.drop_index(
        "ix_observation_events_tenant_actor_ts",
        table_name="observation_events",
        schema="observation",
    )
    op.drop_table("observation_events", schema="observation")

    op.drop_column("tenants", "observation_scope")
    op.drop_column("tenants", "observation_retention_aggregated_days")
    op.drop_column("tenants", "observation_retention_raw_days")
    op.alter_column(
        "tenants", "audit_retention_days", new_column_name="retention_days"
    )

    op.execute("DROP SCHEMA IF EXISTS observation")
