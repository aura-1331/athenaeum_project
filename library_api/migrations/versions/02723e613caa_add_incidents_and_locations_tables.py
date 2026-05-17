from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "02723e613caa"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "archive_incidents",
        sa.Column("incident_id", sa.Integer(), primary_key=True),
        sa.Column("serial_no", sa.Integer(), nullable=False),
        sa.Column("incident_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="MEDIUM"),
        sa.Column("reported_by", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="OPEN"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "reported_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("resolved_at", sa.DateTime(), nullable=True)
    )

    op.create_table(
        "item_locations",
        sa.Column("location_id", sa.Integer(), primary_key=True),
        sa.Column("serial_no", sa.Integer(), nullable=False),
        sa.Column("location_name", sa.String(length=100), nullable=False),
        sa.Column("moved_by", sa.Integer(), nullable=False),
        sa.Column(
            "moved_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("notes", sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_table("item_locations")
    op.drop_table("archive_incidents")