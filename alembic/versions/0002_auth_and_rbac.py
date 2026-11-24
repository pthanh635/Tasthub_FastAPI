"""auth and rbac schema

Revision ID: 0002_auth_and_rbac
Revises: 0001_initial_schema
Create Date: 2026-11-09 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_auth_and_rbac"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema with user roles, project status, and refresh tokens."""
    user_role_enum = sa.Enum("ADMIN", "MEMBER", name="user_role_enum")
    user_role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role_enum,
            server_default="MEMBER",
            nullable=False,
        ),
    )

    project_status_enum = sa.Enum(
        "ACTIVE",
        "ARCHIVED",
        name="project_status_enum",
    )
    project_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "projects",
        sa.Column(
            "status",
            project_status_enum,
            server_default="ACTIVE",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_projects_status"),
        "projects",
        ["status"],
        unique=False,
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint(
            "token_hash",
            name=op.f("uq_refresh_tokens_token_hash"),
        ),
    )
    op.create_index(
        op.f("ix_refresh_tokens_jti"),
        "refresh_tokens",
        ["jti"],
        unique=True,
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"),
        "refresh_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade auth and rbac schema changes."""
    op.drop_index(
        op.f("ix_refresh_tokens_user_id"),
        table_name="refresh_tokens",
    )
    op.drop_index(
        op.f("ix_refresh_tokens_jti"),
        table_name="refresh_tokens",
    )
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_column("projects", "status")
    sa.Enum(name="project_status_enum").drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "role")
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)

