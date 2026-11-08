# Backend giai đoạn 4: Đặt vé & Chống bán trùng — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết lại `GET /api/orders` và `POST /api/orders` của server Node bằng FastAPI + PostgreSQL, giữ nguyên JSON, mã lỗi và câu báo lỗi. Bảo đảm **không bao giờ bán vượt số vé còn lại hoặc bán trùng ghế** khi nhiều người mua cùng lúc. Kèm `python -m app.seed --demo` tạo đơn mẫu rải trong 7 ngày.

**Architecture:**
- `app/services/booking.py` chứa toàn bộ logic đặt vé trong **một transaction**. Router `app/routers/orders.py` chỉ nhận request, gọi service và trả kết quả.
- **Chống bán vượt (bán theo loại vé hoặc theo khu):** dùng *UPDATE có điều kiện nguyên tử*:
  `UPDATE tier_stock SET sold = sold + :q WHERE … AND presold + sold + :q <= capacity RETURNING …`.
  - Không có dòng nào trả về nghĩa là hết vé: rollback cả đơn, trả 409.
  - Dòng được khoá theo thứ tự `tier_id` tăng dần, nên hai đơn mua chéo hạng vé không bị deadlock.
  - CHECK `presold + sold <= capacity` ở CSDL là lớp chặn cuối cùng.
- **Chống bán trùng ghế:** `INSERT INTO seat_holds … ON CONFLICT DO NOTHING RETURNING seat_id`. Ghế nào không được trả về nghĩa là đã có người mua: rollback, trả 409 kèm tên ghế. Khoá chính `(event_id, show_id, seat_id)` là lớp chặn cuối cùng.
- Deadlock hoặc xung đột tuần tự hoá còn sót lại đã được `errors.py` (giai đoạn 2) chuyển thành 409 "Hệ thống đang bận, vui lòng thử lại".

**Tech Stack:** FastAPI, SQLAlchemy 2.1 (đồng bộ, `insert().on_conflict_do_nothing().returning()`, `update().returning()`), PostgreSQL 18 (READ COMMITTED mặc định), pytest + `ThreadPoolExecutor` để test chạy đồng thời.

**Spec:** `docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 6 "Đặt vé", mục 5 `--demo`, mục 7 dòng giai đoạn 4). Nguồn hành vi chuẩn: `server/app.js` dòng 34–59 (mã), 86–113 (`toOrderJson`), 255–360 (`/orders`).

## Global Constraints

- **Không tạo git commit** (người dùng yêu cầu). Không sửa `server/`, `src/`.
- Đường dẫn NFD: `cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip`. Ghi file qua Write vào scratchpad rồi `cp`/ghép bằng Python. Gọi script với đường dẫn có dấu cách thì đặt trong ngoặc kép. Lệnh có tham số `/…` thì đặt `MSYS_NO_PATHCONV=1`.
- Test: `cd backend && .venv/Scripts/python.exe -m pytest -p no:cacheprovider`.
- Câu báo lỗi (chép nguyên văn từ Node):
  - 404 `Sự kiện không tồn tại`
  - 400 `Sự kiện chưa mở bán`
  - 400 `Suất diễn không hợp lệ`
  - 400 `Vui lòng nhập họ tên người nhận vé`
  - 400 `Email nhận vé không hợp lệ`
  - 400 `Số điện thoại không hợp lệ`
  - 400 `Phương thức thanh toán không hợp lệ`
  - 400 `Vui lòng chọn ít nhất 1 ghế`
  - 400 `Mỗi đơn tối đa 10 vé`
  - 400 `Ghế không hợp lệ`
  - 409 `Ghế {row}{num} ({label}) vừa có người mua`
  - 400 `Số lượng vé không hợp lệ`
  - 400 `Vui lòng chọn ít nhất 1 vé`
  - 400 `Hạng vé không hợp lệ`
  - 400 `{tier}: tối đa {max} vé mỗi đơn`
  - 409 `{tier} chỉ còn {left} vé` hoặc `{tier} vừa hết vé`
  - 400 `Mã giảm giá không tồn tại`
  - 400 `Mã {CODE} chỉ áp dụng cho đơn từ {minOrder vi-VN} ₫`. Định dạng số kiểu vi-VN dùng dấu chấm, ví dụ `500.000`.
- **Mới so với Node:** 400 `Suất diễn này đã diễn ra` khi `starts_at <= now()`. Node vẫn cho mua vé suất đã qua, mình coi đó là lỗi (ghi Ruling).
- `MAX_PER_ORDER = 10`. `PAYMENT_METHODS = ("qr", "wallet", "card")`. Mã giảm giá đọc từ bảng `coupons` (`active`, không phân biệt hoa thường).
- Bảng chữ cái của mã: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, sinh bằng `secrets`.
  - Mã đơn `TN` + 8 ký tự.
  - Mã vé `XXXX-XXXX`.
- Chỉ bán sự kiện công khai (`public_events_query`), suất và hạng vé `active`. Sự kiện của Ban tổ chức chưa có dòng `tier_stock` thì tạo dòng đó ngay trong transaction (`INSERT … ON CONFLICT DO NOTHING`, `capacity` lấy từ `ticket_tiers`, `presold = 0`).
- JSON đơn hàng giữ đúng khoá của `toOrderJson`: `id, slug, title, showId, start (ISO +07:00), startTime, endTime, venue, address, items[{tierId,name,price,qty}], tickets[{code,tierId,name,price,seat,checkedInAt}], subtotal, discount, coupon, total, method, status, buyer{name,email,phone}, createdAt (ISO +07:00)`.

## Review Focus

1. **Nhiều người mua cùng lúc hạng vé sắp hết**: không bao giờ bán vượt. Ví dụ còn 5 vé, 20 request song song mỗi request 1 vé thì đúng 5 thành công. Test thuộc Task 2.
2. **Hai người cùng giành một ghế**: đúng 1 người thành công, những người còn lại nhận 409 kèm tên ghế. Test thuộc Task 3.
3. **Đơn mua nhiều hạng vé, có một hạng hết vé giữa chừng**: không được trừ kho một phần. Cả đơn huỷ, kho trả về như cũ. Hai đơn mua chéo hạng vé (A: t1+t2, B: t2+t1) chạy song song không gây deadlock hay lỗi 500. Test thuộc Task 2.
4. **Giá và giảm giá do server tính**: `price` hay `total` client gửi lên bị bỏ qua. Mã giảm giá viết thường vẫn dùng được. Đơn dưới mức tối thiểu thì 400. Test thuộc Task 2.
5. **Không bán sự kiện, suất hay hạng vé đã ngừng bán / chưa mở bán / đã diễn ra**. Mua theo ghế với `showId` của sự kiện khác cũng bị chặn. Test thuộc Task 2 và 3.

---

### Task 1: Mã đơn / mã vé, JSON đơn hàng, `GET /api/orders`

**Files:**
- Create: `backend/app/services/booking.py` (phần mã + `order_json`), `backend/app/routers/orders.py`, `backend/tests/booking_helpers.py`, `backend/tests/test_api_orders_list.py`
- Modify: `backend/app/main.py` (`include_router(orders.router, prefix="/api")`)

**Interfaces — Produces:**
- `booking.ALPHABET`, `booking.random_code(n: int) -> str`.
- `booking.new_order_id(db) -> str`, `booking.new_ticket_code(db) -> str`. Cả hai kiểm tra trùng trong DB như Node.
- `booking.orders_json(db, orders: list[Order]) -> list[dict]`: tối đa 4 truy vấn cho cả danh sách, không N+1.
  - `items.name` và `tickets.name` lấy từ `ticket_tiers.name`.
  - `tickets.seat` = `map_seats.label` (dựa theo `events.map_id`), `null` nếu không phải vé có ghế.
  - Vé xếp theo `ticket_tiers.sort_order`, rồi `map_seats.sort_order`, rồi `code`.
- Route `GET /api/orders` (`require_user`) → `{"orders": [...]}`, chỉ đơn của chính người dùng, mới nhất trước.
- Test helper `booking_helpers.py`:
  - `make_customer(db, email) -> User`
  - `login(client, email, password="matkhau1")`
  - `insert_order(db, user, slug, show_id, items=[(tier_id, qty)], seats=[...], created_at=None) -> Order`: chèn thẳng bằng ORM, dùng để test phần đọc.

- [ ] **Step 1: Test thất bại**

```python
def test_orders_requires_login(c): assert c.get("/api/orders").json() == {"error": "Vui lòng đăng nhập để tiếp tục"}
def test_lists_only_own_orders_newest_first(c, api_db)          # 2 user, mỗi người 2 đơn với created_at khác nhau
def test_order_json_shape_matches_node(c, api_db):
    o = body["orders"][0]
    assert set(o) == {"id","slug","title","showId","start","startTime","endTime","venue","address","items","tickets",
                      "subtotal","discount","coupon","total","method","status","buyer","createdAt"}
    assert o["start"].endswith("+07:00") and o["items"][0] == {"tierId": ..., "name": ..., "price": ..., "qty": 2}
    assert len(o["tickets"]) == 2 and all(re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", t["code"]) for t in o["tickets"])
def test_seat_ticket_has_seat_label(c, api_db)                    # đơn ghế: tickets[].seat == map_seats.label
def test_random_codes_use_unambiguous_alphabet(): assert set(random_code(500)) <= set(ALPHABET) and not set("IO01") & set(ALPHABET)
```
  Fixture: dùng `api_db` / `api` (catalog đã nạp, phạm vi module) cùng `c` (client mới). Teardown xoá các tài khoản `%@x.vn` (dọn theo dây chuyền cả đơn, vé, `seat_holds` có `order_id`). Riêng `tier_stock.sold` phải được trả về 0 trong `finally`.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 2: `POST /api/orders` cho sự kiện bán theo loại vé / theo khu

**Files:** Create `backend/tests/test_api_orders_create.py`. Modify `services/booking.py`, `routers/orders.py`.

**Interfaces — Produces:**
- `OrderIn{slug, showId, items, seats, buyer, method, coupon: Any}`. Dùng `as_str` để ép kiểu, như phần tài khoản.
- `booking.create_order(db, user: User, body: OrderIn) -> Order`. Thứ tự xử lý:
  1. Kiểm tra theo đúng thứ tự Node: event → mở bán → show (không gửi `showId` thì lấy suất active sớm nhất) → **suất đã diễn ra** → buyer → method.
  2. Dòng đơn: gộp các mục cùng `tierId`; kiểm tra qty là số nguyên > 0, hạng vé active, `qty <= max_per_order`; tổng ≤ 10.
  3. Tính `subtotal` theo giá trong DB, áp mã giảm giá (`total = subtotal − discount`).
  4. **Trừ kho theo thứ tự `tier_id`** bằng UPDATE có điều kiện. Thất bại thì đọc lại số còn để báo lỗi `chỉ còn N vé` / `vừa hết vé`.
  5. Chèn `orders`, `order_items`, `tickets` (mỗi vé một mã).
- Mọi lỗi nghiệp vụ là `HTTPException`. Route trả 201 `{"order": order_json}`.
- `layout == "seats"` → sang Task 3. Trong task này, nhánh `seats` ném `NotImplementedError`.

- [ ] **Step 1: Test thất bại** (sự kiện kiểu list và zones lấy từ `legacy_events.json`; người mua `BUYER = {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}`)

```python
def test_create_list_order_201_and_stock_decreases(c, logged_in, api_db):
    before = remaining(c, LIST, tier)
    r = c.post(ORDERS, json=order(LIST, items=[{"tierId": tier, "qty": 2}]))
    assert r.status_code == 201
    o = r.json()["order"]; assert o["total"] == 2 * price and len(o["tickets"]) == 2 and o["status"] == "paid"
    assert remaining(c, LIST, tier) == before - 2
    assert c.get("/api/orders").json()["orders"][0]["id"] == o["id"]
def test_zone_order_respects_presold(c, logged_in, api_db)                 # còn = capacity - presold; mua đúng số còn → 201; mua thêm 1 → 409 "… vừa hết vé"
def test_client_prices_are_ignored(c, logged_in)                           # gửi items[].price=1, total=1 → total vẫn theo giá trong DB
def test_coupon_lowercase_applies(c, logged_in)                            # "nhip50" với đơn ≥ 500.000 → discount 50000, coupon "NHIP50"
def test_coupon_min_order_400(c, logged_in)                                # đơn < 500.000 → "Mã NHIP50 chỉ áp dụng cho đơn từ 500.000 ₫"
def test_unknown_coupon_400(c, logged_in)                                  # "Mã giảm giá không tồn tại"
@pytest.mark.parametrize("patch,status,msg", [... đủ các câu Global Constraints cho list: event, show, buyer x3, method, qty, no items, bad tier, tier max, 11 vé ...])
def test_validation_messages(c, logged_in, patch, status, msg)
def test_requires_login_401(c)
def test_coming_event_400(c, logged_in, api_db)                            # sale_start tương lai → "Sự kiện chưa mở bán"
def test_past_show_400(c, logged_in, api_db)                               # chỉnh starts_at về quá khứ → "Suất diễn này đã diễn ra"
def test_inactive_show_and_tier_rejected(c, logged_in, api_db)
def test_org_event_without_stock_row_is_bookable(c, logged_in, api_db)    # make_org_event (giai đoạn 2), không có tier_stock → 201, tier_stock được tạo, sold=qty
def test_multi_tier_order_is_all_or_nothing(c, logged_in, api_db)          # t1 còn nhiều, t2 còn 1, mua t1×2 + t2×2 → 409; sold của t1 không đổi
# --- đồng thời ---
def test_parallel_buyers_never_oversell(api, api_db, customers):
    # đặt capacity sao cho còn đúng 5; 20 luồng × 1 vé, mỗi luồng TestClient riêng đã đăng nhập
    assert codes.count(201) == 5 and codes.count(409) == 15
    assert stock.presold + stock.sold == stock.capacity and tickets_in_db == 5
def test_crossed_multi_tier_orders_do_not_deadlock(api, api_db, customers):
    # 10 luồng: nửa mua [t1, t2], nửa mua [t2, t1], đủ vé → mọi mã đều 201, không có 500/409 "bận"
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.** Chạy riêng 2 test đồng thời thêm 5 lần để chắc không chập chờn.
- [ ] **Step 5:** Ghi ledger.

---

### Task 3: `POST /api/orders` cho sự kiện bán theo ghế

**Files:** Create `backend/tests/test_api_orders_seats.py`. Modify `services/booking.py`.

**Interfaces — Produces:**
- Nhánh `seats` của `create_order`:
  1. `seats` lấy duy nhất từ body (giữ thứ tự). Rỗng thì 400. Quá 10 ghế thì 400.
  2. Tra từng ghế trong `map_seats` của `events.map_id`. Không có thì `Ghế không hợp lệ`.
  3. Ghế có trong `seat_holds` của suất thì 409, báo đúng ghế đầu tiên bị trùng.
  4. Nhóm ghế theo `group_id` thành hạng vé (`ticket_tiers.id == group_id`, phải active).
  5. Tính `subtotal`, áp mã giảm giá.
  6. Chèn đơn trước, rồi `INSERT seat_holds(order_id) … ON CONFLICT DO NOTHING RETURNING seat_id`. Thiếu ghế nào thì rollback và trả 409 với ghế đó, sắp theo thứ tự trong yêu cầu.
  7. Chèn mỗi ghế một vé, kèm `seat_id`.

- [ ] **Step 1: Test thất bại**

```python
def test_seat_order_201_tickets_have_labels(c, logged_in)                  # 2 ghế trống → 201; tickets[].seat == label; availability unavailableSeats chứa 2 ghế
def test_presold_seat_409_with_label(c, logged_in)                         # ghế đã bán sẵn → 409 "Ghế {row}{num} ({label}) vừa có người mua"
def test_seat_validation(c, logged_in)                                     # [] → "Vui lòng chọn ít nhất 1 ghế"; 11 ghế → "Mỗi đơn tối đa 10 vé"; "X-Z99" → "Ghế không hợp lệ"
def test_duplicate_seat_ids_in_request_count_once(c, logged_in)            # ["G-D5","G-D5"] → 1 vé
def test_coupon_on_seat_order(c, logged_in)
def test_parallel_same_seat_exactly_one_wins(api, api_db, customers):      # 10 luồng cùng 1 ghế → 1×201, 9×409; seat_holds có đúng 1 dòng có order_id
def test_parallel_overlapping_seat_sets_no_double_sale(api, api_db, customers):
    # 8 luồng, mỗi luồng 2 ghế liền kề chồng lên nhau (A1+A2, A2+A3, …) → không ghế nào thuộc 2 đơn; số ghế đã giữ = 2 × số đơn thành công
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** (chạy riêng test đồng thời 5 lần) → ghi ledger.

---

### Task 4: `python -m app.seed --demo`, Postman, README

**Files:** Modify `backend/app/seed.py`, `backend/tests/test_seed.py`, Postman, `backend/README.md`.

**Interfaces — Produces:**
- `seed.load_demo(db, *, days: int = 7, orders_per_day: tuple[int, int] = (3, 8), rng_seed: int = 7) -> int`. Trả số đơn đã tạo.
  - Tạo (hoặc dùng lại) 5 khách `khach{1..5}@demo.ticketnhip.vn` (mật khẩu `demo123456`).
  - **Xoá các đơn demo cũ** trước khi tạo, gồm cả việc trả lại kho: các đơn của tài khoản `@demo.ticketnhip.vn`.
  - Tạo đơn qua **chính `create_order`**, chọn ngẫu nhiên sự kiện bán theo loại vé hoặc theo khu còn vé và suất chưa diễn. Khoảng 1/4 số đơn dùng mã `NHIP50` khi đủ điều kiện.
  - Đổi `created_at` lùi về ngày tương ứng trong 7 ngày gần nhất (giờ VN, có cả hôm nay).
  - Sự kiện "sắp mở bán" bị `create_order` từ chối thì bỏ qua.
- CLI: `--demo` chạy sau `load_catalog`. Không truyền `--demo` thì không đụng tới đơn demo.

- [ ] **Step 1: Test thất bại** (`test_seed.py`)

```python
def test_demo_orders_spread_over_7_days_and_rerun_replaces(seeded):
    n = load_demo(seeded); seeded.commit()
    days = {d for (d,) in seeded.execute(text("select distinct day from v_daily_revenue"))}
    assert n > 0 and len(days) == 7
    sold = seeded.scalar(select(func.sum(TierStock.sold)))
    load_demo(seeded); seeded.commit()
    assert seeded.scalar(select(func.count()).select_from(Order)) == n          # không nhân đôi
    assert seeded.scalar(select(func.sum(TierStock.sold))) == sold              # kho trả lại rồi trừ lại đúng bằng nhau (cùng rng_seed)
def test_demo_orders_are_consistent(seeded):    # mọi đơn: total = subtotal - discount; số vé = sum(qty); sold khớp tổng qty theo hạng
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.**
- [ ] **Step 5:** Postman thư mục "3 · Đặt vé": "Đăng nhập khách demo", "Đặt vé theo loại vé" (POST), "Vé của tôi" (GET), "Đặt ghế đã bán (409)". README §10 bảng API, mô tả cơ chế chống bán trùng, lệnh `--demo`. Chạy `python -m app.seed --demo` trên DB dev, rồi gọi thử bằng server thật: đăng nhập demo → đặt vé → xem `/orders` → `/availability` giảm đúng. Ghi ledger.

---

## Kết thúc giai đoạn 4
- `pytest` pass toàn bộ. Các test đồng thời chạy lặp vẫn ổn định.
- DB dev có đơn demo trong 7 ngày, `v_daily_revenue` có 7 dòng. Đây là dữ liệu cho dashboard giai đoạn 7.
- Review toàn bộ phần thay đổi bằng một reviewer mới.
