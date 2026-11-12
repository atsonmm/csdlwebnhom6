"""Migration 0010: bảng địa giới sau sáp nhập (34 tỉnh / 3.321 phường xã), khoá ngoại ghép events → wards, logo BTC"""
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import Event
from app.models.locations import Province, Ward
from app.models.users import Organizer, User
from tests.conftest import event_kwargs

HA_NOI, HCM = 1, 79


def test_seeded_counts(db):
    assert db.scalar(select(func.count()).select_from(Province)) == 34
    assert db.scalar(select(func.count()).select_from(Ward)) == 3321
    assert db.get(Province, HA_NOI).short_name == "Hà Nội"
    assert db.get(Province, HCM).short_name == "TP.HCM"


def _ward_of(db, province: int) -> int:
    return db.scalar(select(Ward.code).where(Ward.province_code == province).order_by(Ward.code).limit(1))


def test_event_with_ward_of_its_province_ok(db, make_category):
    db.add(Event(**event_kwargs(make_category.id, province_code=HA_NOI, ward_code=_ward_of(db, HA_NOI), street="1 Tràng Tiền")))
    db.flush()


def test_ward_of_other_province_rejected_by_fk(db, make_category):
    db.add(Event(**event_kwargs(make_category.id, province_code=HA_NOI, ward_code=_ward_of(db, HCM))))
    with pytest.raises(IntegrityError, match="fk_events_ward"):
        db.flush()


def test_ward_needs_province_check(db, make_category):
    db.add(Event(**event_kwargs(make_category.id, ward_code=_ward_of(db, HA_NOI))))
    with pytest.raises(IntegrityError, match="ck_events_ward_needs_province"):
        db.flush()


def test_organizer_logo_column(db):
    u = User(name="BTC", email="logo-btc@btc.vn", password_hash="h", role="organizer")
    db.add(u)
    db.flush()
    db.add(Organizer(user_id=u.id, org_name="BTC", phone="0912345678", logo_url="/api/uploads/" + "a" * 32 + ".png"))
    db.flush()
