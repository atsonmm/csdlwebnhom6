"""Lỗi luôn trả dạng {"error": "..."} giống API Node cũ"""
from datetime import datetime, timezone

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app
from app.utils.timefmt import hhmm, iso_vn

probe = APIRouter(prefix="/api/_probe")


@probe.get("/int")
def _int(n: int) -> dict:
    return {"n": n}


@probe.get("/deadlock")
def _deadlock() -> dict:
    import psycopg.errors
    from sqlalchemy.exc import OperationalError

    raise OperationalError("UPDATE tier_stock ...", {}, psycopg.errors.DeadlockDetected("deadlock detected"))


@probe.get("/canceled")
def _canceled() -> dict:
    import psycopg.errors
    from sqlalchemy.exc import OperationalError

    raise OperationalError("SELECT ...", {}, psycopg.errors.QueryCanceled("canceling statement"))


@probe.get("/boom")
def _boom() -> dict:
    raise RuntimeError("nổ thử")


@pytest.fixture
def client_with_probe():
    app.include_router(probe)
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.router.routes[:] = [r for r in app.router.routes if not getattr(r, "path", "").startswith("/api/_probe")]


def test_unknown_api_route_returns_vietnamese_404(client):
    r = client.get("/api/khong-co")
    assert r.status_code == 404
    assert r.json() == {"error": "Không tìm thấy API"}


def test_validation_error_returns_400_error_shape(client_with_probe):
    r = client_with_probe.get("/api/_probe/int?n=abc")
    assert r.status_code == 400
    assert r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}


def test_unhandled_exception_returns_500_without_trace(client_with_probe):
    r = client_with_probe.get("/api/_probe/boom")
    assert r.status_code == 500
    assert r.json() == {"error": "Lỗi máy chủ, vui lòng thử lại sau"}


def test_iso_vn_formats_vietnam_offset():
    assert iso_vn(datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)) == "2026-11-15T19:00:00+07:00"
    assert iso_vn(None) is None
    assert hhmm(datetime(2026, 11, 15, 12, 30, tzinfo=timezone.utc)) == "19:30"


def test_wrong_method_returns_vietnamese_405_with_allow_header(client):
    r = client.request("DELETE", "/api/health", json={})  # JSON để qua middleware chỉ-nhận-JSON
    assert r.status_code == 405
    assert r.json() == {"error": "Phương thức không được hỗ trợ cho API này"}
    assert "GET" in r.headers.get("allow", "")


def test_deadlock_is_409_retry_not_db_down(client_with_probe):
    r = client_with_probe.get("/api/_probe/deadlock")
    assert r.status_code == 409 and r.json() == {"error": "Hệ thống đang bận, vui lòng thử lại"}


def test_other_operational_errors_are_500_not_db_down(client_with_probe):
    r = client_with_probe.get("/api/_probe/canceled")
    assert r.status_code == 500 and r.json() == {"error": "Lỗi máy chủ, vui lòng thử lại sau"}
