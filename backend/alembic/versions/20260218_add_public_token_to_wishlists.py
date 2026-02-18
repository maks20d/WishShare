from alembic import op
import sqlalchemy as sa


revision = "20260218_add_public_token"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wishlists",
        sa.Column("public_token", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ux_wishlists_public_token",
        "wishlists",
        ["public_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_wishlists_public_token", table_name="wishlists")
    op.drop_column("wishlists", "public_token")
