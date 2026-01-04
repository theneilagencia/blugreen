"""add ON DELETE CASCADE to all foreign keys referencing project

Revision ID: add_cascade_delete_fks
Revises: add_assumption_fields
Create Date: 2026-01-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_cascade_delete_fks'
down_revision = 'add_assumption_fields'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add ON DELETE CASCADE to all foreign keys referencing project table.
    
    This ensures that when a project is deleted, all related records in:
    - product
    - project_agent
    - quality_metric
    - task
    - workflow
    
    are automatically deleted by the database, preventing IntegrityError.
    """
    
    # 1. product.project_id
    op.drop_constraint('product_project_id_fkey', 'product', type_='foreignkey')
    op.create_foreign_key(
        'product_project_id_fkey',
        'product', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 2. project_agent.project_id
    op.drop_constraint('project_agent_project_id_fkey', 'project_agent', type_='foreignkey')
    op.create_foreign_key(
        'project_agent_project_id_fkey',
        'project_agent', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 3. quality_metric.project_id
    op.drop_constraint('quality_metric_project_id_fkey', 'quality_metric', type_='foreignkey')
    op.create_foreign_key(
        'quality_metric_project_id_fkey',
        'quality_metric', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 4. task.project_id
    op.drop_constraint('task_project_id_fkey', 'task', type_='foreignkey')
    op.create_foreign_key(
        'task_project_id_fkey',
        'task', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 5. workflow.project_id
    op.drop_constraint('workflow_project_id_fkey', 'workflow', type_='foreignkey')
    op.create_foreign_key(
        'workflow_project_id_fkey',
        'workflow', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    """
    Revert foreign keys to NO ACTION (default behavior).
    """
    
    # 1. product.project_id
    op.drop_constraint('product_project_id_fkey', 'product', type_='foreignkey')
    op.create_foreign_key(
        'product_project_id_fkey',
        'product', 'project',
        ['project_id'], ['id']
    )
    
    # 2. project_agent.project_id
    op.drop_constraint('project_agent_project_id_fkey', 'project_agent', type_='foreignkey')
    op.create_foreign_key(
        'project_agent_project_id_fkey',
        'project_agent', 'project',
        ['project_id'], ['id']
    )
    
    # 3. quality_metric.project_id
    op.drop_constraint('quality_metric_project_id_fkey', 'quality_metric', type_='foreignkey')
    op.create_foreign_key(
        'quality_metric_project_id_fkey',
        'quality_metric', 'project',
        ['project_id'], ['id']
    )
    
    # 4. task.project_id
    op.drop_constraint('task_project_id_fkey', 'task', type_='foreignkey')
    op.create_foreign_key(
        'task_project_id_fkey',
        'task', 'project',
        ['project_id'], ['id']
    )
    
    # 5. workflow.project_id
    op.drop_constraint('workflow_project_id_fkey', 'workflow', type_='foreignkey')
    op.create_foreign_key(
        'workflow_project_id_fkey',
        'workflow', 'project',
        ['project_id'], ['id']
    )
