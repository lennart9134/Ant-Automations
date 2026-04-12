"""Initial schema: audit_events, tenants, approval_requests, approval_steps.

Revision ID: 001
Revises: None
Create Date: 2026-04-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Tenants ---
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("domain", sa.String(256), server_default=""),
        sa.Column("workflow_templates", JSONB, server_default="{}"),
        sa.Column("connector_configs", JSONB, server_default="{}"),
        sa.Column("approval_policies", JSONB, server_default="{}"),
        sa.Column("feature_flags", JSONB, server_default="{}"),
        sa.Column("data_residency", sa.String(32), server_default="eu-west-1"),
        sa.Column("retention_days", sa.Integer, server_default="90"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Audit events (append-only) ---
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(128), index=True),
        sa.Column("tenant_id", sa.String(128), index=True),
        sa.Column("actor", sa.String(256), server_default=""),
        sa.Column("resource", sa.String(256), server_default=""),
        sa.Column("action", sa.String(256), server_default=""),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("model_input", sa.Text, nullable=True),
        sa.Column("model_output", sa.Text, nullable=True),
        sa.Column("risk_level", sa.String(16), server_default="low"),
        sa.Column("outcome", sa.String(32), server_default="success"),
    )

    # --- Approval requests ---
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("correlation_id", sa.String(128), server_default=""),
        sa.Column("workflow_run_id", sa.String(128), index=True),
        sa.Column("action_description", sa.Text, server_default=""),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending", index=True),
        sa.Column("timeout_seconds", sa.Integer, server_default="3600"),
        sa.Column("escalation_target", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Approval steps ---
    op.create_table(
        "approval_steps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("approval_requests.id"), nullable=False, index=True),
        sa.Column("approver_id", sa.String(256), nullable=False),
        sa.Column("required", sa.Boolean, server_default="true"),
        sa.Column("decided", sa.Boolean, server_default="false"),
        sa.Column("decision", sa.String(32), server_default="pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.Text, server_default=""),
        sa.UniqueConstraint("request_id", "approver_id"),
    )


def downgrade() -> None:
    op.drop_table("approval_steps")
    op.drop_table("approval_requests")
    op.drop_table("audit_events")
    op.drop_table("tenants")
