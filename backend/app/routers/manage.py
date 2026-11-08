"""API Ban tổ chức & Quản trị sàn — giống server/manage.js của bản Node
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/manage_controller.py"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.middlewares.auth import require_role, require_user
from app.config.database import get_db
from app.models.users import User
from app.services import manage
from app.schemas.manage import OrganizerIn, ReviewIn
from app.controllers import manage_controller as ctrl

router = APIRouter(tags=["Ban tổ chức & Quản trị"])


@router.post("/organizer/register", status_code=201)
def organizer_register(body: OrganizerIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    """Khách đăng ký trở thành Ban tổ chức (đăng ký lại = cập nhật hồ sơ)"""
    return ctrl.organizer_register(body, user, db)


@router.get("/organizer/me")
def organizer_me(user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Hồ sơ + sự kiện (kèm số vé bán, doanh thu) + hoá đơn mới của chính Ban tổ chức"""
    return ctrl.organizer_me(user, db)


@router.post("/organizer/events", status_code=201)
def organizer_create_event(body: manage.OrgEventIn, user: User = Depends(require_role("organizer")),
                           db: Session = Depends(get_db)) -> dict:
    """Tạo sự kiện mới → trạng thái chờ duyệt"""
    return ctrl.organizer_create_event(body, user, db)


@router.get("/admin/overview")
def admin_overview(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)) -> dict:
    """Hồ sơ chờ duyệt, 10 đơn mới nhất, số liệu toàn sàn"""
    return ctrl.admin_overview(_admin, db)


@router.post("/admin/events/{event_id}/review")
def admin_review(event_id: str, body: ReviewIn, _admin: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db)) -> dict:
    """Duyệt (approve) hoặc trả lại (reject, kèm lý do) sự kiện của Ban tổ chức"""
    return ctrl.admin_review(event_id, body, _admin, db)


@router.get("/organizer/stats")
def organizer_stats(days: int = Query(7, ge=1, le=31), user: User = Depends(require_role("organizer")),
                    db: Session = Depends(get_db)) -> dict:
    """Doanh thu + số vé theo ngày (giờ VN) của các sự kiện thuộc Ban tổ chức — cho biểu đồ dashboard"""
    return ctrl.organizer_stats(days, user, db)


@router.get("/organizer/events/{event_id}")
def organizer_event(event_id: str, user: User = Depends(require_role("organizer")), db: Session = Depends(get_db)) -> dict:
    """Chi tiết một sự kiện của chính Ban tổ chức (ngăn kéo trên dashboard)"""
    return ctrl.organizer_event(event_id, user, db)
