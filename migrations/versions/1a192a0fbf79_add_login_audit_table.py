from alembic import op
import sqlalchemy as sa

revision = '1a192a0fbf79'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'login_audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('login_id', sa.Integer()),
        sa.Column('role', sa.String()),
        sa.Column('login_name', sa.String()),
        sa.Column('action', sa.String()),
        sa.Column('device_used', sa.String()),
        sa.Column('ip_address', sa.String()),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('login_audit_log')