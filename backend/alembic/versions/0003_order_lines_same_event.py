"""order_lines_same_event

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 23:22:41.325781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ("order_items", "seat_holds", "tickets")


def upgrade() -> None:
    """Dòng đơn / vé / ghế giữ phải cùng sự kiện với đơn hàng: FK ghép (order_id, event_id)"""
    op.create_unique_constraint("uq_orders_id_event", "orders", ["id", "event_id"])
    for t in TABLES:
        op.drop_constraint(f"{t}_order_id_fkey", t, type_="foreignkey")
        op.create_foreign_key(f"fk_{t}_order_event", t, "orders", ["order_id", "event_id"], ["id", "event_id"], ondelete="CASCADE")


def downgrade() -> None:
    for t in TABLES:
        op.drop_constraint(f"fk_{t}_order_event", t, type_="foreignkey")
        op.create_foreign_key(f"{t}_order_id_fkey", t, "orders", ["order_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_orders_id_event", "orders", type_="unique")
