"""add alert_record table

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-03 11:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alertrecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "alert_type",
            sa.Enum("user_80_pct", "user_100_pct", "global_spend", name="alerttype"),
            nullable=False,
        ),
        sa.Column(
            "period", sqlmodel.sql.sqltypes.AutoString(length=7), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "alert_type", "period"),
    )
    op.create_index(
        op.f("ix_alertrecord_user_id"), "alertrecord", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_alertrecord_user_id"), table_name="alertrecord")
    op.drop_table("alertrecord")
    sa.Enum(name="alerttype").drop(op.get_bind(), checkfirst=True)
