"""normalize product into its own table with foreign keys

Introduces a `products` parent table (one row per trading pair) and turns
the `product` string column on candles/order_book_snapshots/trades/narrations
into a `product_id` foreign key — a real one-to-many relationship instead of
four independent tables that happened to share a string value.

Revision ID: 82b8e0e137cb
Revises: ddc885d3b597
Create Date: 2026-10-14 01:59:03.912041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82b8e0e137cb'
down_revision: Union[str, Sequence[str], None] = 'ddc885d3b597'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHILD_TABLES = ["candles", "order_book_snapshots", "trades", "narrations"]


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index(op.f("ix_products_symbol"), "products", ["symbol"], unique=True)

    # Backfill: one products row per distinct value seen across all four
    # tables (in practice just "BTC-USD" so far, but this stays correct if
    # more than one pair was ever streamed before this migration).
    op.execute(
        """
        INSERT INTO products (symbol)
        SELECT DISTINCT product FROM (
            SELECT product FROM candles
            UNION SELECT product FROM order_book_snapshots
            UNION SELECT product FROM trades
            UNION SELECT product FROM narrations
        ) AS all_products
        ON CONFLICT (symbol) DO NOTHING
        """
    )

    for table in CHILD_TABLES:
        op.add_column(table, sa.Column("product_id", sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {table} SET product_id = products.id "
            f"FROM products WHERE products.symbol = {table}.product"
        )
        op.alter_column(table, "product_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_product_id", table, "products", ["product_id"], ["id"]
        )
        op.drop_index(f"ix_{table}_product", table_name=table)
        op.create_index(f"ix_{table}_product_id", table, ["product_id"])

    # candles had a (product, ts) uniqueness guarantee — recreate it on the FK column
    op.drop_constraint("uq_candles_product_ts", "candles", type_="unique")
    op.drop_column("candles", "product")
    op.create_unique_constraint("uq_candles_product_ts", "candles", ["product_id", "ts"])

    for table in ["order_book_snapshots", "trades", "narrations"]:
        op.drop_column(table, "product")


def downgrade() -> None:
    op.add_column("candles", sa.Column("product", sa.String(), nullable=True))
    for table in ["order_book_snapshots", "trades", "narrations"]:
        op.add_column(table, sa.Column("product", sa.String(), nullable=True))

    for table in CHILD_TABLES:
        op.execute(
            f"UPDATE {table} SET product = products.symbol "
            f"FROM products WHERE products.id = {table}.product_id"
        )
        op.alter_column(table, "product", nullable=False)
        op.drop_index(f"ix_{table}_product_id", table_name=table)
        op.drop_constraint(f"fk_{table}_product_id", table, type_="foreignkey")
        op.drop_column(table, "product_id")
        op.create_index(f"ix_{table}_product", table, ["product"])

    op.drop_constraint("uq_candles_product_ts", "candles", type_="unique")
    op.create_unique_constraint("uq_candles_product_ts", "candles", ["product", "ts"])

    op.drop_index(op.f("ix_products_symbol"), table_name="products")
    op.drop_table("products")
