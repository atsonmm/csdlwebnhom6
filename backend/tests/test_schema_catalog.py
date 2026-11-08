import pytest
from sqlalchemy.exc import IntegrityError

from app.models.catalog import Event, HomeSlot, MapZone
from tests.conftest import event_kwargs


def test_list_event_cannot_have_map(db, make_category, make_map):
    db.add(Event(**event_kwargs(make_category.id, layout="list", map_id=make_map.id)))
    with pytest.raises(IntegrityError, match="ck_events_layout_map"):
        db.flush()


def test_zone_event_requires_map(db, make_category):
    db.add(Event(**event_kwargs(make_category.id, layout="zones", map_id=None)))
    with pytest.raises(IntegrityError, match="ck_events_layout_map"):
        db.flush()


def test_zone_capacity_must_be_positive(db, make_map):
    db.add(MapZone(map_id=make_map.id, id="z", label="Z", group_id="vip", capacity=0, shape={}, text=[]))
    with pytest.raises(IntegrityError):
        db.flush()


def test_event_slug_unique(db, make_event):
    db.add(Event(**event_kwargs(make_event.category_id)))
    with pytest.raises(IntegrityError, match="slug"):
        db.flush()


def test_home_slot_rejects_unknown_section(db, make_event):
    db.add(HomeSlot(section="banner", position=1, event_id=make_event.id, meta={}))
    with pytest.raises(IntegrityError):
        db.flush()
