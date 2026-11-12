"""Bảng câu hỏi khi đặt vé: event_questions (BTC dựng) + order_answers (người mua trả lời)

- event_questions(event_id, id, kind consent|text|choice, label, help, required, options jsonb, sort_order)
  CHECK: câu 'choice' phải có options là mảng JSON; xoá sự kiện chưa có đơn → câu hỏi đi theo (CASCADE)
- order_answers(order_id, question_id, event_id, value, label_snapshot)
  FK (order_id, event_id) → orders ON DELETE CASCADE; FK (event_id, question_id) → event_questions ON DELETE RESTRICT
  → câu hỏi đã có người trả lời không xoá được (cùng quy tắc với hạng vé đã có đơn)
Bảng mới, không đụng dữ liệu cũ. Hạ phiên bản: xoá hai bảng (mất mọi câu hỏi / câu trả lời).

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: Union[str, Sequence[str], None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_questions",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id", sa.String(30), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("help", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("event_id", "id"),
        sa.CheckConstraint("kind IN ('consent','text','choice')", name="ck_event_questions_kind"),
        sa.CheckConstraint("kind <> 'choice' OR (options IS NOT NULL AND jsonb_typeof(options) = 'array')",
                           name="ck_event_questions_options"),
        comment="Câu hỏi khi đặt vé do ban tổ chức dựng cho từng sự kiện (đồng ý điều khoản, nhập chữ, chọn một)",
    )
    op.create_table(
        "order_answers",
        sa.Column("order_id", sa.String(20), nullable=False),
        sa.Column("question_id", sa.String(30), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("label_snapshot", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("order_id", "question_id"),
        sa.ForeignKeyConstraint(["order_id", "event_id"], ["orders.id", "orders.event_id"], ondelete="CASCADE",
                                name="fk_order_answers_order_event"),
        sa.ForeignKeyConstraint(["event_id", "question_id"], ["event_questions.event_id", "event_questions.id"],
                                ondelete="RESTRICT", name="fk_order_answers_question"),
        comment="Câu trả lời của người mua cho một đơn; label_snapshot chụp lại nhãn câu hỏi lúc trả lời",
    )


def downgrade() -> None:
    op.drop_table("order_answers")
    op.drop_table("event_questions")
