"""add activity_log and admin_setting tables

Revision ID: a1b2c3d4e5f7
Revises: cc713b150da9
Create Date: 2026-04-03 10:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "cc713b150da9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activitylog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "login",
                "logout",
                "rename",
                "settings_change",
                "user_created",
                "user_deleted",
                "limit_changed",
                "api_key_changed",
                name="activityaction",
            ),
            nullable=False,
        ),
        sa.Column("detail", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activitylog_user_id"), "activitylog", ["user_id"], unique=False)

    op.create_table(
        "adminsetting",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("value", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_adminsetting_key"), "adminsetting", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_adminsetting_key"), table_name="adminsetting")
    op.drop_table("adminsetting")
    op.drop_index(op.f("ix_activitylog_user_id"), table_name="activitylog")
    op.drop_table("activitylog")
    sa.Enum(name="activityaction").drop(op.get_bind(), checkfirst=True)
