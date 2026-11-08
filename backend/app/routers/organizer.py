"""API vận hành của Ban tổ chức (giai đoạn 2): sổ đơn, báo cáo, soát vé, sửa/huỷ sự kiện, rút tiền
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/organizer_controller.py"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.middlewares.auth import require_role
from app.config.database import get_db
from app.models.users import User
from app.services import manage
from app.schemas.organizer import CheckinIn, CancelIn, WithdrawalIn
from app.controllers import organizer_controller as ctrl

router = APIRouter(tags=["Ban tổ chức — vận hành"])


@router.get("/organizer/orders")
def organizer_orders(q: str = "", eventId: str = "", status: str = "all", day_from: str = Query("", alias="from"),
                     to: str = "", page: str = "1", pageSize: str = "20",
                     user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Sổ đơn: tìm theo mã đơn / tên / email / SĐT, lọc sự kiện, trạng thái, khoảng ngày (giờ VN), phân trang"""
    return ctrl.organizer_orders(q, eventId, status, day_from, to, page, pageSize, user, db)


@router.get("/organizer/reports")
def organizer_reports(day_from: str = Query("", alias="from"), to: str = "", eventId: str = "", groupBy: str = "day",
                      user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Báo cáo doanh thu (mặc định 30 ngày đến hôm nay, giờ VN): tổng, chuỗi theo ngày/tuần/tháng, theo sự kiện, theo hạng vé"""
    return ctrl.organizer_reports(day_from, to, eventId, groupBy, user, db)


@router.post("/organizer/checkin")
def organizer_checkin(body: CheckinIn, user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Soát một mã vé (QR hoặc gõ tay): checked-in lần đầu, already nếu đã soát (kèm giờ soát đầu)"""
    return ctrl.organizer_checkin(body, user, db)


@router.delete("/organizer/events/{event_id}")
def organizer_cancel_event(event_id: str, body: CancelIn | None = None, user: User = Depends(require_role("organizer")),
                           db: Session = Depends(get_db)) -> dict:
    """Huỷ sự kiện: chưa có đơn → xoá hẳn; có đơn → huỷ (ẩn, ngừng bán) + hoàn tiền mọi đơn đã trả. Bắt buộc lý do khi có đơn."""
    return ctrl.organizer_cancel_event(event_id, body, user, db)


@router.patch("/organizer/events/{event_id}")
def organizer_update_event(event_id: str, body: manage.OrgEventIn, user: User = Depends(require_role("organizer")),
                           db: Session = Depends(get_db)) -> dict:
    """Sửa sự kiện: chưa duyệt → sửa toàn bộ; đã duyệt chưa diễn → chỉ phần không ảnh hưởng người đã mua"""
    return ctrl.organizer_update_event(event_id, body, user, db)


@router.get("/organizer/withdrawals")
def organizer_withdrawals(user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Số dư (đã quyết toán / tạm giữ / chờ rút / đã rút / khả dụng) + lịch sử yêu cầu rút tiền (mới trước)"""
    return ctrl.organizer_withdrawals(user, db)


@router.post("/organizer/withdrawals", status_code=201)
def organizer_request_withdrawal(body: WithdrawalIn, user: User = Depends(require_role("organizer")),
                                 db: Session = Depends(get_db)) -> dict:
    """Gửi yêu cầu rút tiền về ngân hàng: tối thiểu 50.000 ₫, không quá số dư khả dụng"""
    return ctrl.organizer_request_withdrawal(body, user, db)


@router.get("/organizer/top-customers")
def organizer_top_customers(day_from: str = Query("", alias="from"), to: str = "",
                            user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Top 10 hạng khách chi nhiều nhất cho các sự kiện của Ban tổ chức trong khoảng ngày (DENSE_RANK)"""
    return ctrl.organizer_top_customers(day_from, to, user, db)


@router.get("/organizer/venue-maps")
def organizer_venue_maps(user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Sơ đồ khu / ghế có sẵn của sàn để Ban tổ chức chọn khi tạo sự kiện (nhóm + sức chứa từng nhóm)"""
    return ctrl.organizer_venue_maps(user, db)
