"""add assumption fields to project

Revision ID: add_assumption_fields
Revises: 
Create Date: 2026-01-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_assumption_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to project table
    op.add_column('project', sa.Column('assumption_status', sa.String(50), nullable=True))
    op.add_column('project', sa.Column('assumption_error', sa.Text(), nullable=True))
    op.add_column('project', sa.Column('detected_branch', sa.String(255), nullable=True))
    op.add_column('project', sa.Column('assumption_started_at', sa.DateTime(), nullable=True))
    op.add_column('project', sa.Column('assumption_completed_at', sa.DateTime(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('project', 'assumption_completed_at')
    op.drop_column('project', 'assumption_started_at')
    op.drop_column('project', 'detected_branch')
    op.drop_column('project', 'assumption_error')
    op.drop_column('project', 'assumption_status')
