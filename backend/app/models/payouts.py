"""Chi trả cho Ban tổ chức: yêu cầu rút tiền về ngân hàng (Admin duyệt đã chuyển / từ chối)"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_withdrawals_amount"),
        CheckConstraint("status IN ('pending','paid','rejected')", name="ck_withdrawals_status"),
        # chờ xử lý ⇔ chưa có thời điểm xử lý
        CheckConstraint("(status = 'pending') = (processed_at IS NULL)", name="ck_withdrawals_processed"),
        # từ chối thì phải có lý do
        CheckConstraint("status <> 'rejected' OR note IS NOT NULL", name="ck_withdrawals_reject_note"),
        Index("ix_withdrawals_organizer_created", "organizer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("organizers.user_id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)
    bank_name: Mapped[str] = mapped_column(Text)
    account_no: Mapped[str] = mapped_column(String(20))
    account_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
