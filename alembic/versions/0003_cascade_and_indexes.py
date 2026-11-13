"""cascade and indexes

Revision ID: 0003_cascade_and_indexes
Revises: 0002_auth_and_rbac
Create Date: 2026-11-12 13:40:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_cascade_and_indexes"
down_revision: str | Sequence[str] | None = "0002_auth_and_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update workspace_members foreign keys to CASCADE
    op.drop_constraint(
        "fk_workspace_members_workspace_id_workspaces",
        "workspace_members",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_workspace_members_workspace_id_workspaces"),
        "workspace_members",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_workspace_members_user_id_users",
        "workspace_members",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_workspace_members_user_id_users"),
        "workspace_members",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. Update projects foreign key to CASCADE
    op.drop_constraint(
        "fk_projects_workspace_id_workspaces",
        "projects",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_projects_workspace_id_workspaces"),
        "projects",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Update labels foreign key to CASCADE
    op.drop_constraint(
        "fk_labels_workspace_id_workspaces",
        "labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_labels_workspace_id_workspaces"),
        "labels",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Update tasks foreign key to CASCADE
    op.drop_constraint(
        "fk_tasks_project_id_projects",
        "tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_tasks_project_id_projects"),
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Update task_labels foreign keys and add index on label_id
    op.drop_constraint(
        "fk_task_labels_task_id_tasks",
        "task_labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_task_labels_task_id_tasks"),
        "task_labels",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_task_labels_label_id_labels",
        "task_labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_task_labels_label_id_labels"),
        "task_labels",
        "labels",
        ["label_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_task_labels_label_id"),
        "task_labels",
        ["label_id"],
        unique=False,
    )

    # 6. Update comments foreign key to CASCADE
    op.drop_constraint(
        "fk_comments_task_id_tasks",
        "comments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_comments_task_id_tasks"),
        "comments",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_comments_task_id_tasks"),
        "comments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_comments_task_id_tasks",
        "comments",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_index(op.f("ix_task_labels_label_id"), table_name="task_labels")

    op.drop_constraint(
        op.f("fk_task_labels_label_id_labels"),
        "task_labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_task_labels_label_id_labels",
        "task_labels",
        "labels",
        ["label_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_task_labels_task_id_tasks"),
        "task_labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_task_labels_task_id_tasks",
        "task_labels",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_tasks_project_id_projects"),
        "tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_tasks_project_id_projects",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_labels_workspace_id_workspaces"),
        "labels",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_labels_workspace_id_workspaces",
        "labels",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_projects_workspace_id_workspaces"),
        "projects",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_projects_workspace_id_workspaces",
        "projects",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_workspace_members_user_id_users"),
        "workspace_members",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_members_user_id_users",
        "workspace_members",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        op.f("fk_workspace_members_workspace_id_workspaces"),
        "workspace_members",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_members_workspace_id_workspaces",
        "workspace_members",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )
