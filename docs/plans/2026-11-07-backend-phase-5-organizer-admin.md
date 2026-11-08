# Backend giai đoạn 5: Ban tổ chức & Quản trị — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết lại các API quản lý của `server/manage.js` bằng FastAPI + PostgreSQL:
- Ban tổ chức: đăng ký, xem bàn làm việc, tạo sự kiện (chờ duyệt).
- Quản trị: tổng quan toàn sàn, duyệt hoặc trả lại sự kiện.

Giữ nguyên JSON và câu báo lỗi để `OrganizerDashboard.jsx` / `AdminDashboard.jsx` dùng thẳng được. Sự kiện được duyệt thì xuất hiện ở API danh mục (giai đoạn 2) và đặt vé được (giai đoạn 4).

**Architecture:**
- `app/services/manage.py` chứa logic (`slugify`, `unique_slug`, `event_summaries` truy vấn theo lô, tạo sự kiện, tổng quan, duyệt).
- `app/routers/manage.py` chứa route, phân quyền bằng `require_user` / `require_role`.
- Sự kiện của Ban tổ chức nằm chung bảng `events` (`organizer_id` khác NULL, `layout='list'`), kèm 1 suất và 1–8 hạng vé `ve-N`.
- **`tier_stock` được tạo luôn lúc tạo sự kiện**, nên kho có sẵn từ đầu.
- **Duyệt sự kiện là thao tác nguyên tử**: `UPDATE … WHERE status='pending' RETURNING`. Hai admin bấm cùng lúc thì chỉ 1 người thành công, người kia nhận 409.

**Tech Stack:** FastAPI, SQLAlchemy 2.1, PostgreSQL 18, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 4 "events gộp", mục 6 API giữ nguyên, mục 7 dòng giai đoạn 5). Nguồn hành vi chuẩn: `server/manage.js` (dòng 63–234).

## Global Constraints

- **Không tạo git commit.** Không sửa `server/`, `src/`. Cách làm với đường dẫn NFD và scratchpad giống các giai đoạn trước.
- Test: `cd backend && .venv/Scripts/python.exe -m pytest -p no:cacheprovider`.
- Câu báo lỗi chép nguyên văn từ `manage.js`:
  - Đăng ký Ban tổ chức (dòng 117–123):
    - 400 `Tài khoản quản trị không thể đăng ký làm Ban tổ chức`
    - 400 `Vui lòng nhập tên đơn vị tổ chức (2–120 ký tự)`
    - 400 `Số điện thoại liên hệ không hợp lệ`
    - 400 `Giới thiệu tối đa 1000 ký tự`
  - Tạo sự kiện (dòng 160–179):
    - `Tên sự kiện cần từ 3 đến 120 ký tự`
    - `Danh mục không hợp lệ`
    - `Vui lòng nhập thành phố` (2–60 ký tự)
    - `Vui lòng nhập địa điểm tổ chức` (2–120 ký tự)
    - `Địa chỉ tối đa 200 ký tự`
    - `Ngày diễn không hợp lệ`
    - `Ngày diễn phải từ hôm nay trở đi` (so theo **ngày giờ Việt Nam**)
    - `Giờ bắt đầu / kết thúc không hợp lệ`
    - `Giờ kết thúc phải sau giờ bắt đầu`
    - `Giới thiệu sự kiện cần từ 20 đến 4000 ký tự`
    - `Cần từ 1 đến 8 loại vé`
    - `Loại vé {i}: vui lòng nhập tên`
    - `Loại vé “{name}”: giá từ 10.000 ₫ đến 100.000.000 ₫`
    - `Loại vé “{name}”: số lượng từ 1 đến 100.000`
  - Duyệt sự kiện (dòng 223–226):
    - 400 `Quyết định không hợp lệ`
    - 404 `Không tìm thấy hồ sơ sự kiện`
    - 409 `Hồ sơ này đã được xử lý`
    - Lý do trả lại mặc định: `Hồ sơ chưa đủ thông tin, vui lòng bổ sung.`
- Hạng vé tạo mới: `id = ve-{i}`, `max_per_order = 10`, `perks` tối đa 200 ký tự. Địa chỉ để trống thì ghi `[ĐỊA CHỈ], {city}`. `description` là các đoạn văn, tách theo dòng trống.
- `events.search_text` = `normalize_vi(f"{title} {city} {venue} {categoryLabel}")`. Cùng công thức với `export_catalog.mjs`, viết thành một hàm dùng chung `app.textnorm.search_text_for`.
- `slugify` giống JS: `normalize_vi` rồi đổi `[^a-z0-9]+` thành `-` và bỏ `-` ở hai đầu. Slug trùng thì thêm hậu tố `-2`, `-3`… Nếu `slugify` ra rỗng thì dùng `su-kien`.
- JSON giữ đúng khoá của Node:
  - `eventSummary`: `{id, slug, title, category, city, venue, date, startTime, status, rejectReason, orgName, createdAt, capacity, minPrice, sold, revenue}`.
  - `recentOrders`: `{id, total, created_at, name, items}`. **Có khoá snake_case `created_at`**, vì UI đọc đúng khoá đó. `items` là chuỗi `"VIP ×2, Thường ×1"`.
  - `organizer`: `{orgName, phone, description, createdAt, code: "ORG-00012"}`.
  - Tổng quan admin: `{pending:[eventSummary], orders:[{id, event, amount, status, createdAt, customer, tickets}], totals:{revenue, orders, tickets, customers, organizers, approvedEvents}}`.
- `sold` = tổng `order_items.qty` của đơn `paid`. `revenue` = tổng `orders.total` của đơn `paid`. Ban tổ chức chịu khoản giảm giá (theo quyết định của người dùng ở thiết kế dashboard).

## Review Focus

1. **Phân quyền:** khách thường gọi `/organizer/me` hay `/organizer/events` nhận 403. Ban tổ chức gọi `/admin/*` nhận 403. Chưa đăng nhập nhận 401. Ban tổ chức chỉ thấy sự kiện và đơn của **chính mình**. Test thuộc Task 2, 3, 4.
2. **Sự kiện chờ duyệt hoặc bị trả lại không công khai và không đặt được.** Sau khi duyệt thì xuất hiện ở `/api/events?organizer=1` và đặt vé được. Test thuộc Task 4.
3. **Hai admin duyệt cùng lúc**: đúng 1 người thành công, người kia nhận 409. Test thuộc Task 4.
4. **Ngày diễn so theo giờ VN**: tạo sự kiện cho "hôm nay" phải được chấp nhận kể cả lúc 23:30 giờ VN (tức 16:30 UTC). Hôm qua thì bị từ chối. Test thuộc Task 3.
5. **Slug trùng tên** (kể cả trùng với sự kiện có sẵn của sàn) phải thêm hậu tố, không được ghi đè sự kiện khác. Tên toàn ký tự đặc biệt thì ra slug `su-kien`. Test thuộc Task 1 và 3.

---

### Task 1: Hàm dùng chung (`slugify`, `search_text_for`, `unique_slug`, `event_summaries`)

**Files:** Create `backend/app/services/manage.py`, `backend/tests/test_manage_helpers.py`. Modify `backend/app/textnorm.py`.

**Interfaces — Produces:**
- `textnorm.slugify(s: str) -> str`
- `textnorm.search_text_for(title, city, venue, category_label) -> str`
- `manage.unique_slug(db, title) -> str`
- `manage.event_summaries(db, events: list[Event]) -> list[dict]`: tối đa 5 truy vấn.
  - `date` là `YYYY-MM-DD` và `startTime`, lấy theo giờ VN từ suất đầu tiên.
  - `capacity` = tổng sức chứa các hạng vé. `minPrice` = giá thấp nhất.
  - `orgName` lấy từ `organizers`.
  - `createdAt` dạng ISO +07:00.

- [ ] **Step 1: Test thất bại**

```python
@pytest.mark.parametrize("raw,slug", [("Đêm Nhạc Mùa Đông 2026", "dem-nhac-mua-dong-2026"), ("  --Hà Nội!!  ", "ha-noi"), ("!!!", "")])
def test_slugify_matches_js(raw, slug)
def test_search_text_formula_matches_catalog_export(api_db)   # với 3 sự kiện có sẵn: search_text_for(...) == events.search_text đã nạp
def test_unique_slug_suffixes(api, api_db)                    # tiêu đề trùng sự kiện có sẵn → "-2"; nếu "-2" đã tồn tại → "-3"; "!!!" → "su-kien"
def test_event_summaries_sales_and_shape(api, api_db)         # sự kiện BTC + 2 đơn paid + 1 đơn refunded → sold/revenue chỉ tính paid; đủ khoá
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 2: `POST /api/organizer/register`, `GET /api/organizer/me`

**Files:** Create `backend/app/routers/manage.py`, `backend/tests/test_api_organizer.py`. Modify `backend/app/main.py`.

**Interfaces:**
- `POST /organizer/register` (`require_user`). Body `{orgName, phone, description}`.
  - Upsert vào `organizers` (đăng ký lại thì cập nhật hồ sơ).
  - Đặt `users.role = 'organizer'`.
  - Trả 201 `{"user": public_user}`.
  - Admin gọi thì 400.
  - `phone` lưu dạng chuẩn hoá.
- `GET /organizer/me` (`require_role("organizer")`) → `{organizer, events, recentOrders}`.
  - `events` xếp theo ngày diễn.
  - `recentOrders` gồm 6 đơn mới nhất của các sự kiện thuộc Ban tổ chức này.

- [ ] **Step 1: Test thất bại**

```python
def test_register_turns_customer_into_organizer(c, logged_customer)    # 201; /auth/me role organizer; organizers row phone chuẩn hoá
def test_register_again_updates_profile(c, logged_customer)
@pytest.mark.parametrize(... 3 câu lỗi ...) def test_register_validation(c, logged_customer, body, msg)
def test_admin_cannot_register(c, logged_admin)                         # 400 câu cố định
def test_register_requires_login(c)                                    # 401
def test_me_requires_organizer_role(c, logged_customer)                 # 403 "Tài khoản của bạn không có quyền…"
def test_me_empty_shape(c, logged_organizer):
    body = c.get("/api/organizer/me").json()
    assert body["organizer"]["code"] == f"ORG-{uid:05d}" and body["events"] == [] and body["recentOrders"] == []
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 3: `POST /api/organizer/events` + `/organizer/me` có số liệu bán

**Files:** Create `backend/tests/test_api_organizer_events.py`. Modify `services/manage.py`, `routers/manage.py`.

**Interfaces:**
- `manage.create_org_event(db, user, body) -> Event`. Theo đúng thứ tự kiểm tra của Node. Kết quả tạo ra:
  - `Event`: `status = 'pending'`, `layout = 'list'`, `search_text`, `description` (danh sách đoạn văn).
  - 1 `Show`: `id = YYYYMMDD-HHMM`, `starts_at` theo giờ VN, `end_time`.
  - Các `TicketTier` `ve-N` và `TierStock` tương ứng (`capacity = quantity`, `presold = 0`).
- Route trả 201 `{"event": eventSummary}`.
- `recentOrders` trong `/organizer/me`: `items` dạng `"Tên hạng ×qty"` nối bằng `", "`, theo thứ tự hạng vé. `created_at` dạng ISO +07:00. `name` là tên người mua (tài khoản đặt).

- [ ] **Step 1: Test thất bại**

```python
def test_create_event_201_pending_with_stock(c, logged_organizer, api_db)   # summary status pending; DB: show id, starts_at = 12:30Z cho 19:30; tier_stock capacity = quantity
def test_pending_event_not_public(c, logged_organizer)                     # /api/events/{slug} 404; không có trong /api/events?organizer=1
def test_slug_unique_against_catalog(c, logged_organizer)                  # title trùng sự kiện có sẵn → slug "...-2"
def test_date_today_accepted_late_evening_vn(c, logged_organizer, monkeypatch)  # đóng băng "now" = 23:30 VN → date hôm nay OK, hôm qua 400
@pytest.mark.parametrize(... đủ 14 câu lỗi ...) def test_create_validation(c, logged_organizer, patch, msg)
def test_customer_cannot_create_403(c, logged_customer)
def test_me_lists_own_events_with_sales(c, logged_organizer, api_db)     # tạo sự kiện → admin duyệt (trực tiếp DB) → khách đặt 2 vé → me: sold 2, revenue = total, recentOrders[0].items == "Vé thường ×2"
def test_me_does_not_show_other_organizers_events(c, api_db)
```
  Muốn đóng băng thời gian thì tách hàm `manage.now_utc()` và monkeypatch hàm này.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 4: `GET /api/admin/overview`, `POST /api/admin/events/{id}/review`

**Files:** Create `backend/tests/test_api_admin.py`. Modify `services/manage.py`, `routers/manage.py`.

**Interfaces:**
- `manage.overview(db) -> dict`:
  - `pending`: các sự kiện `pending`, cũ nhất trước.
  - `orders`: 10 đơn mới nhất toàn sàn, mỗi đơn gồm `event` (tiêu đề), `amount` (`total`), `customer` (tên tài khoản), `tickets` (số vé), `createdAt`.
  - `totals`: `revenue` (tổng `total` của đơn `paid`), `orders`, `tickets`, `customers` (role `customer`), `organizers`, `approvedEvents` (chỉ sự kiện có `organizer_id`).
- `manage.review(db, event_id: int, decision: str, reason: str) -> dict`:
  - Gồm một câu `UPDATE events SET status, reject_reason, reviewed_at = now() WHERE id = :id AND organizer_id IS NOT NULL AND status = 'pending' RETURNING slug, status`.
  - Không có dòng trả về: nếu sự kiện tồn tại thì 409, không tồn tại thì 404.
  - `reason` cắt còn 300 ký tự. Bị trả lại mà để trống lý do thì dùng câu mặc định.
- Route `POST /admin/events/{id}/review`: `id` không phải số thì 404 (bắt ở route, không để rơi về 400 chung). Trả `{"ok": true, "slug", "status"}`.

- [ ] **Step 1: Test thất bại**

```python
def test_overview_requires_admin(c, logged_organizer)                 # 403; chưa đăng nhập 401
def test_overview_shape_and_totals(c, logged_admin, api_db)            # có 1 pending + đơn demo nhỏ → khoá & số đúng
def test_approve_makes_event_public_and_bookable(c, logged_admin, api_db)  # review approve → /api/events?organizer=1 có; khách đặt được 201
def test_reject_with_default_reason(c, logged_admin, api_db)           # reason "" → reject_reason mặc định; vẫn 404 công khai; /organizer/me hiện rejectReason
def test_second_review_409(c, logged_admin, api_db)
def test_unknown_or_catalog_event_404(c, logged_admin, api_db)         # id không có / sự kiện của sàn (organizer_id NULL) / "abc" → 404 "Không tìm thấy hồ sơ sự kiện"
def test_bad_decision_400(c, logged_admin, api_db)
def test_parallel_reviews_exactly_one_wins(api_db, c)                  # 6 admin client cùng lúc (Barrier) approve/reject lẫn lộn → đúng 1×200, 5×409
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 5: Postman, README, chạy thử thật

- [ ] Postman thư mục "4 · Ban tổ chức & Quản trị":
  - Đăng ký Ban tổ chức (dùng tài khoản postman ở thư mục 2).
  - Tạo sự kiện (tự lưu `eventId` vào biến collection).
  - Bàn làm việc Ban tổ chức.
  - Đăng nhập admin.
  - Tổng quan.
  - Duyệt sự kiện (`{{eventId}}`).
- [ ] README §11 bảng API.
- [ ] Khởi động lại uvicorn (không dùng `--reload`). Chạy thử luồng: khách đăng ký → đăng ký Ban tổ chức → tạo sự kiện → admin duyệt → khách khác đặt vé → Ban tổ chức thấy doanh thu. Dọn dữ liệu thử sau khi xong.
- [ ] Toàn bộ test pass. Gọi reviewer mới.
