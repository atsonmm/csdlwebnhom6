def test_health_reports_postgres_18(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["postgres"].startswith("18")


def test_health_db_down_returns_503_vietnamese(client_bad_db):
    r = client_bad_db.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"error": "Không kết nối được CSDL. Kiểm tra PostgreSQL đang chạy và DATABASE_URL."}


def test_health_returns_503_quickly_when_postgres_unreachable():
    """PostgreSQL chưa bật (cổng đóng): phải trả 503 trong vài giây, không treo"""
    import threading

    from fastapi.testclient import TestClient

    from app.config.database import get_db, make_engine
    from app.main import app
    from sqlalchemy.orm import Session

    eng = make_engine("postgresql+psycopg://ticketnhip:ticketnhip@127.0.0.1:5999/ticketnhip")

    def override():
        with Session(eng) as s:
            yield s

    result = {}

    def call():
        app.dependency_overrides[get_db] = override
        try:
            result["r"] = TestClient(app).get("/api/health")
        finally:
            app.dependency_overrides.pop(get_db, None)

    t = threading.Thread(target=call, daemon=True)
    t.start()
    t.join(timeout=20)
    assert not t.is_alive(), "/api/health treo khi PostgreSQL không chạy"
    assert result["r"].status_code == 503
