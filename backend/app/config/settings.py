"""Cấu hình đọc từ biến môi trường / backend/.env"""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip"
    test_database_url: str = "postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip_test"
    # Mặc định "prod" (an toàn khi quên cấu hình): cookie Secure, không in SQL, không trả devResetUrl.
    # Máy phát triển đặt ENV=dev trong backend/.env (xem .env.example).
    env: Literal["dev", "prod"] = "prod"
    # Cờ Secure của cookie phiên: None = theo ENV (prod → Secure). Đặt COOKIE_SECURE=false khi chạy qua HTTP thuần
    # (máy ảo chưa có HTTPS) — nếu không trình duyệt sẽ không gửi cookie và mọi trang cần đăng nhập đều lỗi.
    cookie_secure: bool | None = None
    admin_email: str = "admin@ticketnhip.vn"
    admin_password: str | None = None
    # Ảnh sự kiện do BTC upload (migration 0009) — ngoài mã nguồn; Docker đặt UPLOAD_DIR=/data/uploads (volume)
    # Giữ vé khi đặt (migration 0018): số phút một đơn 'pending' được giữ chỗ; vòng dọn nền chạy mỗi sweeper_seconds giây (0 = tắt)
    hold_minutes: int = 15
    hold_sweeper_seconds: float = 60.0
    upload_dir: Path = BACKEND_DIR.parent / ".data" / "uploads"


settings = Settings()
