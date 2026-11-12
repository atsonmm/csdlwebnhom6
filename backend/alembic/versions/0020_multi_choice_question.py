"""Bảng câu hỏi: thêm loại "Chọn nhiều câu trả lời" (kind 'multi')

event_questions.kind nhận thêm 'multi' (cùng 'choice' phải có options là mảng JSON). Câu trả lời của người mua cho câu 'multi' lưu
trong order_answers.value dạng mảng JSON (["Nhạc","Hài"]) — không đổi cột. Chỉ nới hai CHECK, dữ liệu cũ nguyên vẹn.
Hạ phiên bản: XOÁ các câu 'multi' và câu trả lời của chúng (không biểu diễn được ở lược đồ cũ) rồi trả ràng buộc cũ.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPTIONS_NEW = "kind NOT IN ('choice','multi') OR (options IS NOT NULL AND jsonb_typeof(options) = 'array')"
OPTIONS_OLD = "kind <> 'choice' OR (options IS NOT NULL AND jsonb_typeof(options) = 'array')"


def upgrade() -> None:
    op.drop_constraint("ck_event_questions_kind", "event_questions", type_="check")
    op.drop_constraint("ck_event_questions_options", "event_questions", type_="check")
    op.create_check_constraint("ck_event_questions_kind", "event_questions", "kind IN ('consent','text','choice','multi')")
    op.create_check_constraint("ck_event_questions_options", "event_questions", OPTIONS_NEW)


def downgrade() -> None:
    op.execute("DELETE FROM order_answers a USING event_questions q "
               "WHERE q.event_id = a.event_id AND q.id = a.question_id AND q.kind = 'multi'")
    op.execute("DELETE FROM event_questions WHERE kind = 'multi'")
    op.drop_constraint("ck_event_questions_options", "event_questions", type_="check")
    op.drop_constraint("ck_event_questions_kind", "event_questions", type_="check")
    op.create_check_constraint("ck_event_questions_kind", "event_questions", "kind IN ('consent','text','choice')")
    op.create_check_constraint("ck_event_questions_options", "event_questions", OPTIONS_OLD)
