"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-06 22:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_workspaces_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_index(
        op.f("ix_workspaces_owner_id"),
        "workspaces",
        ["owner_id"],
        unique=False,
    )

    op.create_table(
        "labels",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_labels_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labels")),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_labels_workspace_name",
        ),
    )
    op.create_index(
        op.f("ix_labels_workspace_id"),
        "labels",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "projects",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_projects_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index(
        op.f("ix_projects_workspace_id"),
        "projects",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "OWNER",
                "ADMIN",
                "EDITOR",
                "VIEWER",
                name="workspace_role_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workspace_members_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_workspace_members_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_members")),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
    )
    op.create_index(
        op.f("ix_workspace_members_user_id"),
        "workspace_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_members_workspace_id"),
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "TODO",
                "IN_PROGRESS",
                "REVIEW",
                "DONE",
                name="task_status_enum",
            ),
            server_default="TODO",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "URGENT",
                name="task_priority_enum",
            ),
            server_default="MEDIUM",
            nullable=False,
        ),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_tasks_assignee_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_tasks_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_tasks_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index(
        op.f("ix_tasks_assignee_id"),
        "tasks",
        ["assignee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_created_by_id"),
        "tasks",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_priority"),
        "tasks",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_project_id"),
        "tasks",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_priority",
        "tasks",
        ["project_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_project_status",
        "tasks",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_status"),
        "tasks",
        ["status"],
        unique=False,
    )

    op.create_table(
        "comments",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_comments_author_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_comments_task_id_tasks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(
        op.f("ix_comments_author_id"),
        "comments",
        ["author_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_comments_task_id"),
        "comments",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "task_labels",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("label_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["label_id"],
            ["labels.id"],
            name=op.f("fk_task_labels_label_id_labels"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_labels_task_id_tasks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("task_id", "label_id", name=op.f("pk_task_labels")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("task_labels")
    op.drop_index(op.f("ix_comments_task_id"), table_name="comments")
    op.drop_index(op.f("ix_comments_author_id"), table_name="comments")
    op.drop_table("comments")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
    op.drop_index("ix_tasks_project_priority", table_name="tasks")
    op.drop_index(op.f("ix_tasks_project_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_priority"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_created_by_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_assignee_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(
        op.f("ix_workspace_members_workspace_id"),
        table_name="workspace_members",
    )
    op.drop_index(
        op.f("ix_workspace_members_user_id"),
        table_name="workspace_members",
    )
    op.drop_table("workspace_members")
    op.drop_index(op.f("ix_projects_workspace_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_labels_workspace_id"), table_name="labels")
    op.drop_table("labels")
    op.drop_index(op.f("ix_workspaces_owner_id"), table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    sa.Enum(name="task_priority_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workspace_role_enum").drop(op.get_bind(), checkfirst=True)

