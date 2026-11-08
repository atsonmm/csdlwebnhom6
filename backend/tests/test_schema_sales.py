import pytest
from sqlalchemy.exc import IntegrityError

from app.models.sales import Order, OrderItem, SeatHold, TierStock


def test_stock_cannot_exceed_capacity(db, make_show_tier):
    e, s, t = make_show_tier
    db.add(TierStock(event_id=e.id, show_id=s.id, tier_id=t.id, capacity=10, presold=6, sold=5))
    with pytest.raises(IntegrityError, match="ck_tier_stock_capacity"):
        db.flush()


def test_same_seat_cannot_be_held_twice(db, make_show_tier):
    e, s, _ = make_show_tier
    db.add(SeatHold(event_id=e.id, show_id=s.id, seat_id="G-A1"))
    db.flush()
    db.add(SeatHold(event_id=e.id, show_id=s.id, seat_id="G-A1"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_order_total_must_equal_subtotal_minus_discount(db, make_show_tier, make_user):
    e, s, _ = make_show_tier
    db.add(Order(id="TN-BBBBBBB", user_id=make_user.id, event_id=e.id, show_id=s.id, subtotal=600000,
                 discount=50000, total=600000, method="qr", buyer_name="B", buyer_email="b@x.vn",
                 buyer_phone="0912345678"))
    with pytest.raises(IntegrityError, match="ck_orders_total"):
        db.flush()


def test_order_item_must_reference_existing_tier(db, make_order):
    db.add(OrderItem(order_id=make_order.id, event_id=make_order.event_id, tier_id="khong-co", price=1, qty=1))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.fixture
def other_event_tier(db, make_category):
    from app.models.catalog import Event, TicketTier
    from tests.conftest import event_kwargs

    e2 = Event(**event_kwargs(make_category.id, slug="su-kien-khac", title="Sự kiện khác"))
    db.add(e2)
    db.flush()
    db.add(TicketTier(event_id=e2.id, id="ve-khac", name="Vé khác", price=100000, capacity=5, max_per_order=6))
    db.flush()
    return e2


def test_order_item_must_belong_to_the_orders_event(db, make_order, other_event_tier):
    db.add(OrderItem(order_id=make_order.id, event_id=other_event_tier.id, tier_id="ve-khac", price=100000, qty=1))
    with pytest.raises(IntegrityError):
        db.flush()


def test_ticket_must_belong_to_the_orders_event(db, make_order, other_event_tier):
    from app.models.sales import Ticket

    db.add(Ticket(code="TK-0000001", order_id=make_order.id, event_id=other_event_tier.id, tier_id="ve-khac", price=100000))
    with pytest.raises(IntegrityError):
        db.flush()
