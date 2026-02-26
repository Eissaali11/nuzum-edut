"""Add composite index on attendance(date, status)

Revision ID: 20260226_add_attendance_composite_index
Revises: None
Create Date: 2026-02-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260226_add_attendance_composite_index'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Composite index to accelerate grouped queries by date and status
    op.create_index('ix_attendance_date_status', 'attendance', ['date', 'status'])
    # Ensure employee/date index exists (idempotent attempt)
    op.create_index('ix_attendance_employee_date', 'attendance', ['employee_id', 'date'])


def downgrade():
    op.drop_index('ix_attendance_date_status', table_name='attendance')
    op.drop_index('ix_attendance_employee_date', table_name='attendance')
