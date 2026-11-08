"""Dạng JSON trả ra của API danh mục (khoá camelCase giống object JS cũ)"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Category(CamelModel):
    id: str
    label: str
    dot: str


class CategoryList(CamelModel):
    categories: list[Category]


class CouponOut(CamelModel):
    code: str
    amount: int
    min_order: int


class EventCard(CamelModel):
    """Thẻ sự kiện (danh sách, trang chủ, sự kiện liên quan)"""

    slug: str
    title: str
    category: str
    category_label: str
    city: str
    venue: str
    start: str
    start_time: str
    min_price: int
    status: str  # "coming" (chưa tới giờ mở bán) hoặc "on-sale"
    sale_opens_at: str | None
    resale_count: int


class ShowOut(CamelModel):
    id: str
    start: str
    start_time: str
    end_time: str
    closed: bool  # suất đã bắt đầu → ngừng bán


class TierOut(CamelModel):
    id: str
    name: str
    price: int
    perks: str
    capacity: int
    remaining: int
    max: int
    group: str | None
    group_label: str | None
    color: str | None


class OrganizerOut(CamelModel):
    name: str
    bio: str


class EventDetail(EventCard):
    marker: str
    address: str
    end_time: str
    shows: list[ShowOut]
    layout: str
    map: str | None
    organizer: OrganizerOut
    description: list[str]
    notes: list[str]
    tiers: list[TierOut]  # remaining theo suất còn mở đầu tiên
    max_per_order: int
    sold_out: bool  # mọi suất còn mở đều hết vé (hoặc không còn suất mở)
    related: list[EventCard]


class TierRemaining(CamelModel):
    id: str
    remaining: int


class Availability(CamelModel):
    """Vé còn lại của một suất; unavailableSeats chỉ có với sự kiện bán theo ghế"""

    show: str
    tiers: list[TierRemaining]
    unavailable_seats: list[str] | None = None


class EventList(CamelModel):
    events: list[EventCard]


class HomeCard(EventCard):
    meta: dict  # chỉ phần trang trí của thẻ (độ nghiêng, số hạng, màu…)


class HomeOut(CamelModel):
    sections: dict[str, list[HomeCard]]
