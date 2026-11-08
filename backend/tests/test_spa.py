"""Chạy thật (ENV=prod): FastAPI phục vụ luôn bản build React (dist/) — mọi đường dẫn không phải /api trả index.html"""
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.middlewares.errors import install_error_handlers
from app.utils.spa import install_spa


def make_app(dist) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    api = APIRouter(prefix="/api")

    @api.get("/ping")
    def ping() -> dict:
        return {"ok": True}

    app.include_router(api)
    install_spa(app, dist)
    return TestClient(app)


def build_dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>TicketNhịp</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return tmp_path


def test_client_routes_get_index_html(tmp_path):
    c = make_app(build_dist(tmp_path))
    for path in ("/", "/su-kien/abc", "/ban-to-chuc?loc=dang-ban"):
        r = c.get(path)
        assert r.status_code == 200 and "text/html" in r.headers["content-type"] and "TicketNhịp" in r.text, path


def test_static_files_are_served(tmp_path):
    c = make_app(build_dist(tmp_path))
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/favicon.svg").status_code == 200


def test_api_still_json_and_unknown_api_404_json(tmp_path):
    c = make_app(build_dist(tmp_path))
    assert c.get("/api/ping").json() == {"ok": True}
    r = c.get("/api/khong-co")
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy API"}


def test_missing_asset_is_404_not_index(tmp_path):
    c = make_app(build_dist(tmp_path))
    assert c.get("/assets/khong-co.js").status_code == 404


def test_cannot_escape_dist_with_dot_dot(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    build_dist(dist)
    (tmp_path / "bi-mat.txt").write_text("MAT-KHAU", encoding="utf-8")
    c = make_app(dist)
    for path in ("/%2e%2e/bi-mat.txt", "/..%2fbi-mat.txt", "/assets/%2e%2e/%2e%2e/bi-mat.txt"):
        r = c.get(path)
        assert "MAT-KHAU" not in r.text, path
