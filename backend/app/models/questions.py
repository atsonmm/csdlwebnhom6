"""Bảng câu hỏi khi đặt vé (migration 0019): BTC dựng câu hỏi cho từng sự kiện, người mua trả lời ở bước giữa
"chọn vé" và "thanh toán". Câu hỏi đã có câu trả lời không xoá được (RESTRICT) — cùng quy tắc với hạng vé."""
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class EventQuestion(Base):
    __tablename__ = "event_questions"
    __table_args__ = (
        CheckConstraint("kind IN ('consent','text','choice','multi')", name="ck_event_questions_kind"),
        # câu chọn phải có danh sách lựa chọn (mảng JSON); độ dài 2–8 do tầng dịch vụ kiểm
        CheckConstraint("kind NOT IN ('choice','multi') OR (options IS NOT NULL AND jsonb_typeof(options) = 'array')",
                        name="ck_event_questions_options"),
    )

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # consent = tick đồng ý, text = nhập chữ, choice = chọn một, multi = chọn nhiều
    label: Mapped[str] = mapped_column(Text)
    help: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    options: Mapped[list | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class OrderAnswer(Base):
    """Câu trả lời của một đơn; label_snapshot chụp lại nhãn câu hỏi lúc trả lời (BTC sửa nhãn sau này không đổi lịch sử)"""

    __tablename__ = "order_answers"
    __table_args__ = (
        ForeignKeyConstraint(["order_id", "event_id"], ["orders.id", "orders.event_id"], ondelete="CASCADE",
                             name="fk_order_answers_order_event"),
        ForeignKeyConstraint(["event_id", "question_id"], ["event_questions.event_id", "event_questions.id"],
                             ondelete="RESTRICT", name="fk_order_answers_question"),
    )

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer)
    value: Mapped[str] = mapped_column(Text)
    label_snapshot: Mapped[str] = mapped_column(Text)
