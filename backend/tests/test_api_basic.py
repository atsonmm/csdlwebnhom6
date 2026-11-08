from sqlalchemy import update

from app.models.sales import Coupon


def test_categories_in_display_order(api):
    r = api.get("/api/categories")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert [c["id"] for c in cats][:2] == ["nhac-song", "san-khau"]
    assert cats[0] == {"id": "nhac-song", "label": "Nhạc sống", "dot": "bg-tomato"}


def test_coupon_lookup_is_case_insensitive(api):
    r = api.get("/api/coupons/nhip50")
    assert r.status_code == 200
    assert r.json() == {"code": "NHIP50", "amount": 50000, "minOrder": 500000}


def test_unknown_or_inactive_coupon_404(api, api_db):
    assert api.get("/api/coupons/KHONGCO").json() == {"error": "Mã giảm giá không hợp lệ"}
    try:
        api_db.execute(update(Coupon).values(active=False))
        api_db.commit()
        assert api.get("/api/coupons/NHIP50").status_code == 404
    finally:
        api_db.execute(update(Coupon).values(active=True))
        api_db.commit()
