"""API đơn hàng — giống /api/orders của server Node
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/orders_controller.py"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.middlewares.auth import require_user
from app.config.database import get_db
from app.models.users import User
from app.services import booking
from app.controllers import orders_controller as ctrl

router = APIRouter(prefix="/orders", tags=["Đặt vé"])


@router.get("")
def my_orders(user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    """Đơn của chính người dùng, mới nhất trước"""
    return ctrl.my_orders(user, db)


@router.post("", status_code=201)
def create(body: booking.OrderIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    """Tạo đơn: bán theo loại vé / khu {slug, showId, items:[{tierId, qty}]} hoặc theo ghế {slug, showId, seats:[...]}.
    Giá, số vé còn lại, mã giảm giá đều do máy chủ kiểm tra; cả đơn trong một transaction."""
    return ctrl.create(body, user, db)
