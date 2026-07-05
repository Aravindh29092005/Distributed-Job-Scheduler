"""Production-grade initial schema migration

Revision ID: 20260704_001_initial
Revises: None
Create Date: 2026-07-04 12:00:00.000000

Contains all tables with:
- UUID primary keys
- Composite indexes with query justification  
- Constraints (FK, check, unique)
- Soft-delete support (archived_at)
- Timezone-aware timestamps
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260704_001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    job_type_enum = postgresql.ENUM(
        "immediate", "delayed", "scheduled", "recurring", "batch",
        name="job_type",
        create_type=True
    )
    job_type_enum.create(op.get_bind(), checkfirst=True)

    job_status_enum = postgresql.ENUM(
        "Queued", "Scheduled", "Claimed", "Running", "Completed", "Failed",
        "Retrying", "DeadLetterQueue", "Cancelled",
        name="job_status",
        create_type=True
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    execution_status_enum = postgresql.ENUM(
        "pending", "running", "succeeded", "failed",
        name="execution_status",
        create_type=True
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)

    retry_strategy_enum = postgresql.ENUM(
        "fixed_delay", "linear", "exponential", "exponential_jitter",
        name="retry_strategy",
        create_type=True
    )
    retry_strategy_enum.create(op.get_bind(), checkfirst=True)

    user_role_enum = postgresql.ENUM(
        "admin", "member", "viewer",
        name="user_role",
        create_type=True
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    log_level_enum = postgresql.ENUM(
        "DEBUG", "INFO", "WARNING", "ERROR",
        name="log_level",
        create_type=True
    )
    log_level_enum.create(op.get_bind(), checkfirst=True)

    # ═════════════════════════════════════════════════════════════════════
    # USERS & AUTHENTICATION
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("email ~ '^[^@]+@[^@]+$'", name="ck_user_email_format"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_archived_at", "users", ["archived_at"])

    # ═════════════════════════════════════════════════════════════════════
    # ORGANIZATIONS & MULTI-TENANCY
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_archived_at", "organizations", ["archived_at"])

    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role_enum, server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_org_member_org_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_member_user_id", "organization_members", ["user_id"])

    # ═════════════════════════════════════════════════════════════════════
    # PROJECTS
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_project_name"),
    )
    op.create_index("idx_project_org_created", "projects", ["organization_id", "created_at"])
    op.create_index("ix_project_archived_at", "projects", ["archived_at"])

    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role_enum, server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_index("ix_project_member_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_member_user_id", "project_members", ["user_id"])

    # ═════════════════════════════════════════════════════════════════════
    # QUEUES & RETRY POLICIES
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_concurrent", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("paused", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_queue_name"),
        sa.CheckConstraint("max_concurrent >= 1", name="ck_queue_max_concurrent"),
        sa.CheckConstraint("priority >= 0", name="ck_queue_priority"),
    )
    op.create_index("ix_queue_project_id", "queues", ["project_id"])
    op.create_index("idx_queue_project_created", "queues", ["project_id", "created_at"])
    op.create_index("ix_queue_archived_at", "queues", ["archived_at"])

    op.create_table(
        "retry_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("strategy", retry_strategy_enum, server_default="exponential_jitter", nullable=False),
        sa.Column("initial_delay_ms", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("max_delay_ms", sa.Integer(), server_default=sa.text("60000"), nullable=False),
        sa.Column("multiplier", sa.Float(), server_default=sa.text("2.0"), nullable=False),
        sa.Column("jitter_factor", sa.Float(), server_default=sa.text("0.1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_retry_policy_name"),
        sa.CheckConstraint("max_retries >= 0", name="ck_retry_max"),
        sa.CheckConstraint("initial_delay_ms >= 0", name="ck_retry_initial_delay"),
        sa.CheckConstraint("max_delay_ms >= initial_delay_ms", name="ck_retry_max_delay"),
        sa.CheckConstraint("multiplier > 1.0", name="ck_retry_multiplier"),
        sa.CheckConstraint("jitter_factor >= 0.0 AND jitter_factor <= 1.0", name="ck_retry_jitter"),
    )
    op.create_index("ix_retry_policy_org_id", "retry_policies", ["organization_id"])
    op.create_index("ix_retry_policy_archived_at", "retry_policies", ["archived_at"])

    # ═════════════════════════════════════════════════════════════════════
    # WORKERS
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host", "port", name="uq_worker_addr"),
    )
    op.create_index("idx_worker_heartbeat", "workers", ["last_heartbeat"], postgresql_where="archived_at IS NULL")
    op.create_index("ix_worker_archived_at", "workers", ["archived_at"])

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_worker_id", "worker_heartbeats", ["worker_id"])
    op.create_index("idx_heartbeat_worker_created", "worker_heartbeats", ["worker_id", "created_at"])

    # ═════════════════════════════════════════════════════════════════════
    # JOBS
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retry_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("job_type", job_type_enum, server_default="immediate", nullable=False),
        sa.Column("status", job_status_enum, server_default="Queued", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), server_default=sa.text("300"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retry_policy_id"], ["retry_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("timeout_seconds > 0", name="ck_job_timeout"),
        sa.CheckConstraint("priority >= 0 AND priority <= 10", name="ck_job_priority"),
    )
    op.create_index("ix_job_queue_id", "jobs", ["queue_id"])
    op.create_index("ix_job_project_id", "jobs", ["project_id"])
    op.create_index("ix_job_retry_policy_id", "jobs", ["retry_policy_id"])
    op.create_index("ix_job_worker_id", "jobs", ["worker_id"])
    op.create_index("ix_job_status", "jobs", ["status"])
    op.create_index("ix_job_correlation_id", "jobs", ["correlation_id"])
    op.create_index("ix_job_idempotency_key", "jobs", ["idempotency_key"])
    op.create_index("ix_job_run_at", "jobs", ["run_at"])
    op.create_index("ix_job_batch_id", "jobs", ["batch_id"])
    op.create_index("ix_job_archived_at", "jobs", ["archived_at"])
    # CRITICAL: Job claim query
    op.create_index(
        "idx_job_claim",
        "jobs",
        ["queue_id", "status", "created_at"],
        postgresql_where="status = 'Queued' AND archived_at IS NULL"
    )
    # Dashboard list jobs by project
    op.create_index(
        "idx_job_project_created",
        "jobs",
        ["project_id", "created_at"],
        postgresql_where="archived_at IS NULL"
    )
    # Batch job tracking
    op.create_index(
        "idx_job_batch_status",
        "jobs",
        ["batch_id", "status"],
        postgresql_where="batch_id IS NOT NULL"
    )

    # ═════════════════════════════════════════════════════════════════════
    # SCHEDULED JOBS
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "scheduled_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retry_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cron_expression", sa.String(255), nullable=False),
        sa.Column("payload_template", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retry_policy_id"], ["retry_policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_job_project_id", "scheduled_jobs", ["project_id"])
    op.create_index("ix_scheduled_job_queue_id", "scheduled_jobs", ["queue_id"])
    op.create_index("ix_scheduled_job_next_run_at", "scheduled_jobs", ["next_run_at"])
    op.create_index("ix_scheduled_job_archived_at", "scheduled_jobs", ["archived_at"])

    # ═════════════════════════════════════════════════════════════════════
    # JOB EXECUTIONS & LOGS
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "job_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", execution_status_enum, server_default="pending", nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("attempt_number > 0", name="ck_execution_attempt"),
    )
    op.create_index("ix_execution_job_id", "job_executions", ["job_id"])
    op.create_index("ix_execution_worker_id", "job_executions", ["worker_id"])
    op.create_index("ix_execution_status", "job_executions", ["status"])
    op.create_index("idx_execution_job_created", "job_executions", ["job_id", "created_at"])

    op.create_table(
        "job_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("job_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", log_level_enum, server_default="INFO", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_execution_id"], ["job_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_execution_id", "job_logs", ["job_execution_id"])
    op.create_index("ix_log_level", "job_logs", ["level"])
    op.create_index("ix_log_correlation_id", "job_logs", ["correlation_id"])
    op.create_index("idx_log_execution_created", "job_logs", ["job_execution_id", "created_at"])

    # ═════════════════════════════════════════════════════════════════════
    # DEAD LETTER QUEUE
    # ═════════════════════════════════════════════════════════════════════

    op.create_table(
        "dead_letter_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("final_attempt_number", sa.Integer(), nullable=False),
        sa.Column("final_error", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dlq_job_id", "dead_letter_queue", ["job_id"])
    op.create_index("ix_dlq_queue_id", "dead_letter_queue", ["queue_id"])
    op.create_index("ix_dlq_created_at", "dead_letter_queue", ["created_at"])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table("dead_letter_queue")
    op.drop_table("job_logs")
    op.drop_table("job_executions")
    op.drop_table("scheduled_jobs")
    op.drop_table("jobs")
    op.drop_table("worker_heartbeats")
    op.drop_table("workers")
    op.drop_table("retry_policies")
    op.drop_table("queues")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS job_type CASCADE")
    op.execute("DROP TYPE IF EXISTS job_status CASCADE")
    op.execute("DROP TYPE IF EXISTS execution_status CASCADE")
    op.execute("DROP TYPE IF EXISTS retry_strategy CASCADE")
    op.execute("DROP TYPE IF EXISTS user_role CASCADE")
    op.execute("DROP TYPE IF EXISTS log_level CASCADE")
