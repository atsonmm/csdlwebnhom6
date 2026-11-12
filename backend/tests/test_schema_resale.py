"""Migration 0016 — ràng buộc của chợ vé bán lại (resale_listings, resale_listing_tickets, orders.kind)"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.resale import ResaleListing, ResaleListingTicket
from app.models.sales import Order, Ticket


@pytest.fixture
def ticket(db, make_order):
    t = Ticket(code="AAAA-0001", order_id=make_order.id, event_id=make_order.event_id, tier_id="ve-1", price=300000)
    db.add(t)
    db.flush()
    return t


def listing(db, order, lid="RSL000000001", **over):
    kw = dict(id=lid, seller_id=order.user_id, event_id=order.event_id, show_id=order.show_id, tier_id="ve-1",
              price=250000, allow_partial=True) | over
    row = ResaleListing(**kw)
    db.add(row)
    db.flush()
    return row


def test_listing_with_ticket_ok(db, make_order, ticket):
    lst = listing(db, make_order)
    db.add(ResaleListingTicket(listing_id=lst.id, ticket_code=ticket.code))
    db.flush()
    assert lst.status == "listed"


def test_same_ticket_cannot_be_listed_twice(db, make_order, ticket):
    a = listing(db, make_order, "RSL000000001")
    b = listing(db, make_order, "RSL000000002")
    db.add(ResaleListingTicket(listing_id=a.id, ticket_code=ticket.code))
    db.flush()
    db.add(ResaleListingTicket(listing_id=b.id, ticket_code=ticket.code))
    with pytest.raises(IntegrityError, match="uq_resale_ticket_listed"):
        db.flush()


def test_sold_row_needs_buyer_order(db, make_order, ticket):
    lst = listing(db, make_order)
    db.add(ResaleListingTicket(listing_id=lst.id, ticket_code=ticket.code, status="sold"))
    with pytest.raises(IntegrityError, match="ck_resale_listing_tickets_sold"):
        db.flush()


def test_price_must_be_positive(db, make_order):
    with pytest.raises(IntegrityError, match="ck_resale_listings_price"):
        listing(db, make_order, price=0)


def test_order_kind_checked(db, make_show_tier, make_user):
    e, s, _ = make_show_tier
    db.add(Order(id="TN-KKKKKKK", user_id=make_user.id, event_id=e.id, show_id=s.id, subtotal=1, discount=0, total=1,
                 method="qr", buyer_name="B", buyer_email="b@x.vn", buyer_phone="0912345678", kind="x"))
    with pytest.raises(IntegrityError, match="ck_orders_kind"):
        db.flush()


def test_old_orders_default_primary(db, make_order):
    db.refresh(make_order)
    assert make_order.kind == "primary"
