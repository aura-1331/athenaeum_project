"""make user_id nullable in audit_logs

Revision ID: 477f8e87ab1c
Revises: 
Create Date: 2026-06-07 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '477f8e87ab1c'
down_revision = '1a192a0fbf79'
branch_labels = None
depends_on = None


def upgrade():
    # Make user_id nullable so failed logins can be recorded
    op.alter_column('audit_logs', 'user_id', nullable=True)
    
    # Update foreign key to allow NULL values
    op.drop_constraint('fk_user_audit', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'fk_user_audit', 'audit_logs', 'users', 
        ['user_id'], ['user_id'], ondelete='SET NULL'
    )


def downgrade():
    # Revert the changes
    op.drop_constraint('fk_user_audit', 'audit_logs', type_='foreignkey')
    op.create_foreign_key('fk_user_audit', 'audit_logs', 'users', ['user_id'], ['user_id'])
    op.alter_column('audit_logs', 'user_id', nullable=False)