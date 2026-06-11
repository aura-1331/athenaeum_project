"""update_audit_log_fk_on_delete_set_null

Revision ID: b7e83661fc4a
Revises: 477f8e87ab1c
Create Date: 2026-06-09 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'b7e83661fc4a'
down_revision = '477f8e87ab1c'
branch_labels = None
depends_on = None

def upgrade():
    # Create the foreign key constraint with ON DELETE SET NULL
    # This ensures audit logs remain if a user is deleted
    op.create_foreign_key(
        'fk_user', 
        'system_audit_log', 
        'users', 
        ['user_id'], 
        ['user_id'], 
        ondelete='SET NULL'
    )

def downgrade():
    # Drop the constraint when reverting the migration
    op.drop_constraint('fk_user', 'system_audit_log', type_='foreignkey')