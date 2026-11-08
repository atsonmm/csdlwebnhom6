"""API Quản trị sàn (giai đoạn 2): sổ đơn toàn sàn, Ban tổ chức, báo cáo, tra mã vé, xem trước / gỡ sự kiện, rút tiền.
Mọi route chỉ dành cho vai trò admin.
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/admin_controller.py"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.middlewares.auth import require_role
from app.config.database import get_db
from app.models.users import User
from app.controllers import admin_controller as ctrl
from app.schemas.organizer import CancelIn, DecideWithdrawalIn

router = APIRouter(tags=["Quản trị sàn — vận hành"])
ADMIN = require_role("admin")


@router.get("/admin/orders")
def admin_orders(q: str = "", eventId: str = "", organizerId: str = "", status: str = "all",
                 day_from: str = Query("", alias="from"), to: str = "", page: str = "1", pageSize: str = "20",
                 _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Sổ đơn toàn sàn: cùng tham số với /organizer/orders, thêm organizerId; mỗi đơn kèm orgName (null = sàn tự bán)"""
    return ctrl.admin_orders(q, eventId, organizerId, status, day_from, to, page, pageSize, _admin, db)


@router.get("/admin/organizers")
def admin_organizers(_admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Danh sách Ban tổ chức trên sàn"""
    return ctrl.admin_organizers(_admin, db)


@router.get("/admin/organizers/{organizer_id}/events")
def admin_organizer_events(organizer_id: str, _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Sự kiện của một Ban tổ chức (mọi trạng thái) kèm số vé, doanh thu, phase"""
    return ctrl.admin_organizer_events(organizer_id, _admin, db)


@router.get("/admin/reports")
def admin_reports(day_from: str = Query("", alias="from"), to: str = "", eventId: str = "", organizerId: str = "",
                  groupBy: str = "day", _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Báo cáo toàn sàn: như /organizer/reports, thêm byOrganizer (sàn tự bán = organizerId null) và totals.platformRevenue"""
    return ctrl.admin_reports(day_from, to, eventId, organizerId, groupBy, _admin, db)


@router.get("/admin/tickets/{code}")
def admin_ticket(code: str, _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Tra cứu mã vé (chỉ xem): vé + đơn + sự kiện, kể cả đơn đã hoàn"""
    return ctrl.admin_ticket(code, _admin, db)


@router.post("/admin/events/{event_id}/cancel")
def admin_cancel_event(event_id: str, body: CancelIn | None = None, _admin: User = Depends(ADMIN),
                       db: Session = Depends(get_db)) -> dict:
    """Gỡ / huỷ sự kiện vi phạm: luôn huỷ mềm (không xoá), lý do 5–300 ký tự bắt buộc, hoàn mọi đơn đã trả"""
    return ctrl.admin_cancel_event(event_id, body, _admin, db)


@router.get("/admin/withdrawals")
def admin_withdrawals(status: str = "pending", _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Yêu cầu rút tiền toàn sàn (status = pending | paid | rejected | all), kèm tên + số dư khả dụng của BTC"""
    return ctrl.admin_withdrawals(status, _admin, db)


@router.post("/admin/withdrawals/{withdrawal_id}/decide")
def admin_decide_withdrawal(withdrawal_id: str, body: DecideWithdrawalIn, _admin: User = Depends(ADMIN),
                            db: Session = Depends(get_db)) -> dict:
    """Đánh dấu đã chuyển (paid) hoặc từ chối (rejected, cần lý do 3–300 ký tự); chỉ xử lý được yêu cầu đang chờ"""
    return ctrl.admin_decide_withdrawal(withdrawal_id, body, _admin, db)


@router.get("/admin/events/stale")
def admin_stale_events(days: str = "7", _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Sự kiện đang mở bán nhưng không có đơn đã thanh toán trong `days` ngày (1–90, mặc định 7)"""
    return ctrl.admin_stale_events(days, _admin, db)


@router.get("/admin/events/{event_id}")
def admin_event_preview(event_id: str, _admin: User = Depends(ADMIN), db: Session = Depends(get_db)) -> dict:
    """Xem trước hồ sơ sự kiện ở MỌI trạng thái: event (cùng JSON trang khán giả, related rỗng), summary, organizer"""
    return ctrl.admin_event_preview(event_id, _admin, db)
