"""API tài khoản — giống /api/auth/* của server Node (đường dẫn, JSON, mã lỗi, câu báo lỗi)
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/auth_controller.py"""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from app.middlewares.auth import current_user
from app.config.database import get_db
from app.models.users import User
from app.middlewares.ratelimit import LoginLimiter, get_login_limiter
from app.schemas.auth import RegisterIn, LoginIn, ForgotIn, ResetIn
from app.controllers import auth_controller as ctrl

router = APIRouter(prefix="/auth", tags=["Tài khoản"])


@router.get("/me")
def me(user: User | None = Depends(current_user)) -> dict:
    return ctrl.me(user)


@router.post("/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> dict:
    return ctrl.register(body, response, db)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    return ctrl.logout(request, response, db)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db),
          limiter: LoginLimiter = Depends(get_login_limiter)) -> dict:
    return ctrl.login(body, request, response, db, limiter)


@router.post("/forgot")
def forgot(body: ForgotIn, request: Request, db: Session = Depends(get_db)) -> dict:
    return ctrl.forgot(body, request, db)


@router.post("/reset")
def reset(body: ResetIn, response: Response, db: Session = Depends(get_db)) -> dict:
    return ctrl.reset(body, response, db)
