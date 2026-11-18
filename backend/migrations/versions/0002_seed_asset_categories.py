"""Seed the six fixed asset categories.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

FIXED_CATEGORIES = (
    ("牡丹", 1),
    ("菊花", 2),
    ("月季", 3),
    ("郁金香", 4),
    ("玫瑰", 5),
    ("太阳花", 6),
)


def upgrade() -> None:
    values = ",\n".join(
        f"('{name}', '{name}', {sort_order})"
        for name, sort_order in FIXED_CATEGORIES
    )
    op.execute(
        f"""
        INSERT INTO asset.categories (name, display_name, sort_order)
        VALUES
        {values}
        ON CONFLICT (name) DO UPDATE
        SET display_name = EXCLUDED.display_name,
            sort_order = EXCLUDED.sort_order,
            updated_at = NOW()
        """
    )


def downgrade() -> None:
    names = ", ".join(f"'{name}'" for name, _ in FIXED_CATEGORIES)
    op.execute(f"DELETE FROM asset.categories WHERE name IN ({names})")
