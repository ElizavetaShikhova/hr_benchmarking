import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), server_default="Новый диалог", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "enterprises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "absences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("absence_type", sa.String(), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_absence_dates"),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enterprise_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["enterprise_id"],
            ["enterprises.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "enterprise_id", name="uq_departments_enterprise"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("analysis_plan", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.Column("result_data", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.Column("is_saved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hr_metric_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enterprise_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("metric_code", sa.String(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("target_value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id", "enterprise_id"],
            ["departments.id", "departments.enterprise_id"],
            name="fk_metric_plan_department",
        ),
        sa.ForeignKeyConstraint(
            ["enterprise_id"],
            ["enterprises.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "enterprise_id",
            "department_id",
            "metric_code",
            "period",
            name="uq_metric_plan_scope",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "employment_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("employment_type", sa.String(), nullable=False),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_employment_dates"),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dismissals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employment_id", sa.Integer(), nullable=False),
        sa.Column("dismissal_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("voluntary", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["employment_id"],
            ["employment_history.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employment_id"),
    )
    op.create_table(
        "salary_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employment_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("salary", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_salary_dates"),
        sa.CheckConstraint("salary >= 0", name="ck_salary_nonnegative"),
        sa.ForeignKeyConstraint(
            ["employment_id"],
            ["employment_history.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("salary_history")
    op.drop_table("dismissals")
    op.drop_table("employment_history")
    op.drop_table("positions")
    op.drop_table("hr_metric_plans")
    op.drop_table("messages")
    op.drop_table("departments")
    op.drop_table("absences")
    op.drop_table("enterprises")
    op.drop_table("employees")
    op.drop_table("conversations")
