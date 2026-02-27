from alembic import op
import sqlalchemy as sa


revision = "20260227_add_is_unavailable_to_gifts"
down_revision = "20260218_add_public_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gifts",
        sa.Column("is_unavailable", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "gifts",
        sa.Column("unavailable_reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gifts", "unavailable_reason")
    op.drop_column("gifts", "is_unavailable")
