"""Replace is_superuser with role enum

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

userrole_enum = sa.Enum('ADMIN', 'USER', 'VIEWER', name='userrole')


def upgrade() -> None:
    userrole_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('user', sa.Column('role', userrole_enum, nullable=True))
    op.execute("UPDATE \"user\" SET role = 'ADMIN' WHERE is_superuser = true")
    op.execute("UPDATE \"user\" SET role = 'VIEWER' WHERE is_superuser = false")
    op.alter_column('user', 'role', nullable=False)
    op.drop_column('user', 'is_superuser')


def downgrade() -> None:
    op.add_column('user', sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.execute("UPDATE \"user\" SET is_superuser = true WHERE role = 'ADMIN'")
    op.execute("UPDATE \"user\" SET is_superuser = false WHERE role != 'ADMIN'")
    op.alter_column('user', 'is_superuser', nullable=False)
    op.drop_column('user', 'role')
    userrole_enum.drop(op.get_bind(), checkfirst=True)
