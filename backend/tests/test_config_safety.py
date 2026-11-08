"""Thiếu cấu hình thì phải AN TOÀN: mặc định là môi trường thật (prod)"""
from app.config.settings import Settings


def test_env_defaults_to_prod_when_not_configured(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    assert Settings(_env_file=None).env == "prod"


def test_dev_env_file_still_selects_dev():
    # backend/.env (sao chép từ .env.example) đặt ENV=dev cho máy phát triển
    assert Settings().env == "dev"
