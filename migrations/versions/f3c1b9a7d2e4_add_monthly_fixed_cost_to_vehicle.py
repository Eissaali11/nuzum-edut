"""add monthly_fixed_cost to vehicle

Revision ID: f3c1b9a7d2e4
Revises: c684569a7d3c
Create Date: 2026-02-27 12:25:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = 'f3c1b9a7d2e4'
down_revision = 'c684569a7d3c'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('vehicle')}
    if 'monthly_fixed_cost' not in columns:
        with op.batch_alter_table('vehicle', schema=None) as batch_op:
            batch_op.add_column(sa.Column('monthly_fixed_cost', sa.Float(), nullable=True, server_default='0'))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('vehicle')}
    if 'monthly_fixed_cost' in columns:
        with op.batch_alter_table('vehicle', schema=None) as batch_op:
            batch_op.drop_column('monthly_fixed_cost')
