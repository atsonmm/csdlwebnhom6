"""Controller — xử lý request/response cho routers/orders.py: API đơn hàng — giống /api/orders của server Node"""
from sqlalchemy.orm import Session
from app.models.users import User
from app.services import booking


def my_orders(user: User, db: Session) -> dict:
    # GET 
    return {"orders": booking.user_orders(db, user.id)}


def create(body: booking.OrderIn, user: User, db: Session) -> dict:
    # POST 
    try:
        order = booking.create_order(db, user, body)
        # Dựng JSON TRƯỚC khi commit: nếu bước này lỗi thì đơn bị huỷ luôn,
        # không có chuyện đơn đã lưu mà khách lại thấy báo lỗi rồi bấm mua lần nữa
        result = {"order": booking.orders_json(db, [order])[0]}
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result
