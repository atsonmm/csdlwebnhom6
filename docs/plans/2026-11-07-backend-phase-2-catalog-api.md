# Backend giai đoạn 2: API đọc danh mục — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI phục vụ toàn bộ dữ liệu danh mục từ PostgreSQL (sự kiện, suất, hạng vé, sơ đồ, trang chủ, vé còn lại, danh mục, mã giảm giá), JSON khớp với cái giao diện React đang dùng, kiểm chứng bằng pytest + Postman.

**Architecture:**
- Router `app/routers/catalog.py` (mỏng) gọi các hàm truy vấn trong `app/services/catalog.py`. Hàm truy vấn trả về Pydantic model ở `app/schemas/catalog.py`, nhờ vậy `/docs` hiện đúng lược đồ.
- Chỉ trả về sự kiện `status='approved' AND active`, suất và hạng vé `active`.
- Lỗi luôn trả dạng `{"error": "..."}` như API Node, xử lý tập trung ở `app/errors.py`.

**Tech Stack:** FastAPI 0.162, SQLAlchemy 2.1 (đồng bộ), Pydantic 2, PostgreSQL 18, pytest; Node chỉ để xuất file đối chiếu.

**Spec:** `docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 6 "API mới cho giao diện", mục 7 dòng giai đoạn 2). Giai đoạn 0–1 đã merge (`backend/`, migrations 0001–0004).

## Global Constraints

- Không sửa `server/`, `src/`. Web Node cũ phải chạy như trước.
- Đường dẫn NFD: luôn `cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip`. Sau Write/Edit thì kiểm tra `ls -d /c/Users/khact/OneDrive/T*/` chỉ còn một "Tài liệu".
- Python: `backend/.venv/Scripts/python.exe` (gọi tắt `$PY`). Test: `cd backend && $PY -m pytest -p no:cacheprovider`.
- Mọi API nằm dưới `/api`. Lỗi luôn là `{"error": "<câu tiếng Việt>"}`.
- Thời gian trả ra dạng ISO có múi giờ **+07:00** (giờ VN). Giờ suất dạng `"HH:MM"`.
- Khoá JSON viết camelCase, giống object JS cũ (`categoryLabel`, `minPrice`, `saleOpensAt`, `resaleCount`).
- Ẩn sự kiện có `active = false` hoặc `status <> 'approved'`, suất và hạng vé có `active = false`. Áp dụng ở **mọi** endpoint.
- Tiền: số nguyên VND.
- Nhánh làm việc: `backend-phase-2` (tách từ `master`).

## Review Focus

1. **Tìm không dấu tiếng Việt**: `q=da lat` phải khớp "Đà Lạt", `q=dem nhac` khớp "Đêm nhạc" (chữ đ/Đ). Test thuộc Task 5.
2. **Dòng `active = false`** không được lộ ra ở bất kỳ endpoint nào: chi tiết, danh sách, trang chủ, vé còn lại, sự kiện liên quan. Test ở Task 3, 4, 5, 6.
3. **Sự kiện của Ban tổ chức đang chờ duyệt hoặc bị trả lại** không được công khai (chi tiết trả 404, không có trong danh sách). Test thuộc Task 3 và 5.
4. **`?show=` là mã suất của sự kiện khác, hoặc của suất đã ngừng bán** → 404 "Suất diễn không tồn tại". Không bao giờ trả `remaining` âm. Test thuộc Task 4.
5. **Giờ trả về phải là giờ VN**, không phải UTC: `start` kết thúc bằng `+07:00`, `startTime` khớp giờ in trên vé cũ. Test thuộc Task 3 (đối chiếu) và Task 5.

---

## Hợp đồng JSON (dùng chung cho mọi task)

**Card** (danh sách, trang chủ, liên quan), schema `EventCard`:
`{ slug, title, category, categoryLabel, city, venue, start, startTime, minPrice, status, saleOpensAt, resaleCount }`
- `start`/`startTime` lấy từ suất active sớm nhất.
- `minPrice` = giá nhỏ nhất trong các hạng active.
- `status` = `"coming"` nếu `sale_start > now()`, ngược lại `"on-sale"`.
- `saleOpensAt` = ISO hoặc `null`.

**Chi tiết**, schema `EventDetail` (mở rộng card, khớp `finalize()` trong `src/lib/events.js`):
`{ ...card, marker, address, endTime, shows:[{id,start,startTime,endTime}], layout, map, organizer:{name,bio}, description:[], notes:[], tiers:[{id,name,price,perks,capacity,remaining,max,group,groupLabel,color}], related:[EventCard] }`
- `map` = mã sơ đồ hoặc `null`. `marker` = `categories.dot`.
- `organizer`:
  - Sự kiện của sàn: `host_name/host_bio`.
  - Sự kiện của Ban tổ chức: `organizers.org_name` và `organizers.description`. Nếu `description` rỗng thì dùng `"Ban tổ chức trên TicketNhịp."`.
- `tiers[].remaining` = vé còn của **suất đầu tiên**, cùng công thức với Task 4.
- `group`/`groupLabel`/`color` lấy từ `map_groups` khi có `group_id`. Không có thì là `null`.
- `max` = `max_per_order`.
- `related`: tối đa 4 sự kiện khác, điểm = `2·(cùng category) + 1·(cùng city)`, cùng điểm thì xếp theo `start`.

---

### Task 1: Dạng lỗi `{error}` cho 404 / 400 / 500 + khung router danh mục

**Files:**
- Create: `backend/app/errors.py`, `backend/app/timefmt.py`, `backend/app/routers/__init__.py`, `backend/app/routers/catalog.py`, `backend/tests/test_errors.py`
- Modify: `backend/app/main.py` (bỏ handler cũ, gọi `install_error_handlers(app)`, `app.include_router(catalog.router, prefix="/api")`)

**Interfaces:**
- Produces:
  - `app.errors.install_error_handlers(app: FastAPI) -> None`
  - `app.errors.not_found(message: str) -> HTTPException` (404)
  - `app.timefmt.VN = ZoneInfo("Asia/Ho_Chi_Minh")`, `iso_vn(dt: datetime | None) -> str | None` (kết quả dạng `2026-11-15T19:00:00+07:00`), `hhmm(dt_or_time) -> str`
  - `app.routers.catalog.router: APIRouter`

- [ ] **Step 1: Test thất bại** `tests/test_errors.py`

```python
def test_unknown_api_route_returns_vietnamese_404(client):
    r = client.get("/api/khong-co")
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy API"}
```
Vì `/api/events` chưa có, test 400 và 500 dùng một router **chỉ dành cho test**, gắn trong fixture `client_with_probe`:
`GET /api/_probe/int?n=` (n: int) và `GET /api/_probe/boom` (ném `RuntimeError`).
```python
def test_validation_error_returns_400_error_shape(client_with_probe):
    r = client_with_probe.get("/api/_probe/int?n=abc")
    assert r.status_code == 400 and r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}

def test_unhandled_exception_returns_500_without_trace(client_with_probe):
    r = client_with_probe.get("/api/_probe/boom")
    assert r.status_code == 500 and r.json() == {"error": "Lỗi máy chủ, vui lòng thử lại sau"}

def test_iso_vn_formats_vietnam_offset():
    assert iso_vn(datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)) == "2026-11-15T19:00:00+07:00"
```
`client_with_probe` dùng `TestClient(app, raise_server_exceptions=False)`.
- [ ] **Step 2: FAIL**: 404 nhận được `{"detail": "Not Found"}`, ImportError `app.timefmt`.
- [ ] **Step 3: Cài đặt**
  - Handler cho `starlette.exceptions.HTTPException`: 404 không có `detail` riêng thì trả "Không tìm thấy API", còn lại trả `{"error": detail}`.
  - Handler `RequestValidationError` → 400 "Dữ liệu gửi lên không hợp lệ".
  - Handler `Exception` → 500 "Lỗi máy chủ, vui lòng thử lại sau", đồng thời ghi log stack trace.
  - Giữ handler `OperationalError` → 503 như cũ.
- [ ] **Step 4: PASS** toàn bộ bộ test (health vẫn pass).
- [ ] **Step 5: Commit** `feat(api): lỗi luôn trả {error} (404/400/500) + khung router danh mục`

---

### Task 2: Fixture CSDL đã nạp + `/categories` + `/coupons/{code}`

**Files:**
- Create: `backend/app/schemas/__init__.py`, `backend/app/schemas/catalog.py`, `backend/app/services/__init__.py`, `backend/app/services/catalog.py`, `backend/tests/test_api_basic.py`
- Modify: `backend/tests/conftest.py`, `backend/app/routers/catalog.py`, `backend/postman/ticketnhip.postman_collection.json`

**Interfaces:**
- Consumes: `app.seed.load_catalog/reset_all`, `client` fixture.
- Produces:
  - Fixture `api` (scope **module**): `reset_all` → `load_catalog(catalog.json)` → commit → trả về `TestClient`. Teardown gọi `reset_all`, để các test lược đồ dùng `make_category` không đụng dữ liệu đã nạp.
  - Fixture `api_db` (module): `Session` trên cùng engine, dùng để test tự chỉnh dữ liệu rồi commit.
  - Schema `Category{id,label,dot}`, `CouponOut{code,amount,minOrder}`.
  - `services.catalog.list_categories(db) -> list[Category]` (sắp theo `sort_order`), `get_coupon(db, code: str) -> CouponOut | None` (không phân biệt hoa thường, chỉ lấy mã `active`).
  - Route `GET /api/categories` → `{"categories": [...]}`. Route `GET /api/coupons/{code}` → CouponOut, hoặc 404 "Mã giảm giá không hợp lệ".

- [ ] **Step 1: Test thất bại**

```python
def test_categories_in_display_order(api):
    r = api.get("/api/categories")
    assert r.status_code == 200
    assert [c["id"] for c in r.json()["categories"]][:2] == ["nhac-song", "san-khau"]

def test_coupon_lookup_is_case_insensitive(api):
    assert api.get("/api/coupons/nhip50").json() == {"code": "NHIP50", "amount": 50000, "minOrder": 500000}

def test_unknown_or_inactive_coupon_404(api, api_db):
    assert api.get("/api/coupons/KHONGCO").json() == {"error": "Mã giảm giá không hợp lệ"}
    api_db.execute(update(Coupon).values(active=False)); api_db.commit()
    assert api.get("/api/coupons/NHIP50").status_code == 404
    api_db.execute(update(Coupon).values(active=True)); api_db.commit()
```
- [ ] **Step 2: FAIL** (404 Không tìm thấy API) → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** (các file `test_schema_*` vẫn pass, chứng tỏ teardown đã dọn sạch).
- [ ] **Step 5:** Thêm thư mục Postman "1 · Danh mục" với 2 request trên, mỗi request có test status. **Commit** `feat(api): /categories, /coupons/{code}`.

---

### Task 3: Chi tiết sự kiện `GET /api/events/{slug}` + đối chiếu với dữ liệu JS cũ

**Files:**
- Create: `backend/seed/dump_legacy_events.mjs`, `backend/tests/fixtures/legacy_events.json` (sinh ra, commit), `backend/tests/test_api_event_detail.py`
- Modify: `schemas/catalog.py`, `services/catalog.py`, `routers/catalog.py`, Postman

**Interfaces:**
- Produces:
  - Schema `EventCard`, `ShowOut`, `TierOut`, `OrganizerOut`, `EventDetail` (theo "Hợp đồng JSON", dùng `alias_generator=to_camel`, `populate_by_name=True`, route trả `by_alias`).
  - `services.catalog.public_events_query() -> Select`: điều kiện `Event.status=='approved'`, `Event.active`, có ít nhất 1 suất active.
  - `services.catalog.to_card(db, event: Event) -> EventCard`.
  - `services.catalog.tier_remaining(db, event: Event, show_id: str) -> dict[str, int]`. Task 4 dùng lại hàm này.
  - `services.catalog.get_event_detail(db, slug: str) -> EventDetail | None`.
  - Route `GET /api/events/{slug}` → EventDetail, hoặc 404 "Sự kiện không tồn tại".
  - `dump_legacy_events.mjs` (chạy `TZ=Asia/Ho_Chi_Minh node backend/seed/dump_legacy_events.mjs`, dùng chung cách kiểm tra múi giờ như `export_catalog.mjs`) ghi ra mỗi sự kiện trong `events` của `src/lib/events.js`, trừ slug alias:
    - các trường: `slug, title, category, categoryLabel, marker, city, venue, address, layout, map, status, saleOpensAt (ISO+07 hoặc null), start, startTime, endTime, minPrice, organizer, description, notes, resaleCount`;
    - `shows:[{id,start,startTime,endTime}]`;
    - `tiers:[{id,name,price,perks,max,group,groupLabel,color}]`.
    - Không ghi `remaining`, vì đó là số liệu thay đổi theo bán vé.

- [ ] **Step 1: Sinh file đối chiếu**: chạy script, file ra phải có 41 sự kiện.
- [ ] **Step 2: Test thất bại** `tests/test_api_event_detail.py`

```python
LEGACY = json.loads((FIXTURES / "legacy_events.json").read_text(encoding="utf-8"))
FIELDS = ["slug","title","category","categoryLabel","marker","city","venue","address","layout","map","status",
          "saleOpensAt","start","startTime","endTime","minPrice","organizer","description","notes","resaleCount"]

@pytest.mark.parametrize("legacy", LEGACY, ids=lambda e: e["slug"])
def test_detail_matches_legacy_event(api, legacy):
    body = api.get(f"/api/events/{legacy['slug']}").json()
    assert {k: body[k] for k in FIELDS} == {k: legacy[k] for k in FIELDS}
    assert body["shows"] == legacy["shows"]
    assert [{k: t[k] for k in legacy["tiers"][0]} for t in body["tiers"]] == legacy["tiers"]

def test_remaining_is_first_show_capacity_minus_presold_and_sold(api, api_db): ...
    # chọn 1 sự kiện zones: remaining == capacity - presold của suất đầu (đọc tier_stock)

def test_unknown_slug_404(api):
    assert api.get("/api/events/khong-co").json() == {"error": "Sự kiện không tồn tại"}

def test_inactive_event_is_hidden(api, api_db):        # đặt active=False → 404, rồi trả lại True
def test_inactive_tier_and_show_are_hidden(api, api_db): # tier/show active=False → không có trong tiers/shows
def test_pending_and_rejected_org_events_are_hidden(api, api_db):  # tạo user+organizer+event pending/rejected → 404
def test_approved_org_event_uses_organizer_profile(api, api_db):
    # event organizer_id, status approved, organizers.description = None
    # → body["organizer"] == {"name": "<org_name>", "bio": "Ban tổ chức trên TicketNhịp."}
def test_related_has_up_to_4_active_others(api):
    rel = api.get(f"/api/events/{LEGACY[0]['slug']}").json()["related"]
    assert 1 <= len(rel) <= 4 and all(r["slug"] != LEGACY[0]["slug"] for r in rel)
```
  Mọi test có sửa dữ liệu phải trả dữ liệu về như cũ ở cuối test (try/finally), vì fixture `api` dùng chung cả module.
- [ ] **Step 3: FAIL** → **Step 4: cài đặt.** Đọc chi tiết bằng tối đa ~6 truy vấn: event+category, shows, tiers left join `map_groups`, organizer, `tier_stock`/`seat_holds` của suất đầu, related. Không truy vấn lặp theo từng hạng vé (tránh N+1).
- [ ] **Step 5: PASS toàn bộ.** Nếu test đối chiếu lệch ở trường nào: hoặc sửa service, hoặc ghi một `Ruling` giải thích vì sao bản DB đúng hơn (ví dụ `remaining`). Không được sửa file đối chiếu bằng tay.
- [ ] **Step 6:** Thêm vào Postman "Chi tiết sự kiện" (`/events/concert-dem-4-hen-giua-tinh-ha`, test có `tiers`). **Commit** `feat(api): chi tiết sự kiện từ PostgreSQL, khớp dữ liệu JS cũ`.

---

### Task 4: Vé còn lại `GET /api/events/{slug}/availability?show=`

**Files:**
- Create: `backend/tests/test_api_availability.py`
- Modify: `services/catalog.py`, `routers/catalog.py`, Postman

**Interfaces:**
- Consumes: `tier_remaining` (Task 3).
- Produces:
  - `services.catalog.availability(db, slug: str, show_id: str | None) -> Availability | None`. Kết quả `Availability{show: str, tiers: [{id, remaining}], unavailableSeats: list[str] | None}`, khớp JSON của Node. Khi `None` thì bỏ hẳn khoá này (`response_model_exclude_none`).
  - Quy tắc tính:
    - `list`/`zones`: `remaining = max(0, capacity - presold - sold)` lấy từ `tier_stock`.
    - `seats`: `remaining` của hạng = số ghế trong `map_seats` thuộc nhóm đó mà **không** có trong `seat_holds` của suất. `unavailableSeats` = mọi `seat_id` có trong `seat_holds` của suất, sắp xếp theo mã.
    - Không có `show` thì lấy suất active sớm nhất.
  - Lỗi: slug không có → 404 "Sự kiện không tồn tại". Show không thuộc sự kiện, hoặc đã ngừng bán → 404 "Suất diễn không tồn tại".

- [ ] **Step 1: Test thất bại**

```python
def test_zones_remaining_subtracts_presold_and_sold(api, api_db):   # đặt sold=2 trên 1 tier_stock → remaining giảm 2
def test_list_event_remaining_equals_capacity_when_nothing_sold(api)
def test_seats_unavailable_includes_presold_and_sold_holds(api, api_db):
    # thêm SeatHold có order_id (tạo order hợp lệ) → seat xuất hiện trong unavailableSeats, remaining nhóm giảm 1
def test_seats_remaining_never_negative(api)
def test_default_show_is_earliest_active(api)
def test_show_of_another_event_is_404(api):
    assert r.json() == {"error": "Suất diễn không tồn tại"}
def test_inactive_show_is_404(api, api_db)
def test_list_event_has_no_unavailable_seats_key(api):
    assert "unavailableSeats" not in api.get(f"/api/events/{LIST_SLUG}/availability").json()
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** (`tier_remaining` của Task 3 đổi sang dùng chung hàm tính này) → **Step 4: PASS toàn bộ** (gồm cả test đối chiếu của Task 3).
- [ ] **Step 5:** Thêm Postman "Vé còn lại". **Commit** `feat(api): vé còn lại theo suất (loại vé, khu, ghế)`.

---

### Task 5: Danh sách sự kiện `GET /api/events`

**Files:**
- Create: `backend/tests/test_api_event_list.py`
- Modify: `services/catalog.py`, `routers/catalog.py`, Postman

**Interfaces:**
- Consumes: `public_events_query`, `to_card` (Task 3).
- Produces:
  - `services.catalog.list_events(db, *, q: str | None, category: str | None, city: str | None, organizer: bool, sort: Literal['start','reviewed'], limit: int) -> list[EventCard]`.
  - `app.textnorm.normalize_vi(s: str) -> str`: chuyển sang chữ thường, tách dấu NFD, bỏ các dấu kết hợp, `đ→d`, gộp khoảng trắng. Phải cho kết quả giống `normalizeVi` JS với cùng đầu vào.
  - Route `GET /api/events`, tham số `q`, `category`, `city`, `organizer: bool=False`, `sort='start'`, `limit: int = Query(60, ge=1, le=200)` → `{"events": [EventCard]}`.
  - Lọc `q`: mọi từ trong `normalize_vi(q)` đều phải có trong `events.search_text` (`ILIKE` từng từ).
  - Lọc `city`: so khớp chính xác.
  - `organizer=1` chỉ lấy sự kiện có `organizer_id`. `sort=reviewed` xếp theo `reviewed_at DESC`. Mặc định xếp theo suất sớm nhất tăng dần.

- [ ] **Step 1: Test thất bại**

```python
def test_default_lists_all_public_events_sorted_by_start(api):
    ev = api.get("/api/events").json()["events"]
    assert len(ev) == 41 and [e["start"] for e in ev] == sorted(e["start"] for e in ev)
    assert all(e["start"].endswith("+07:00") for e in ev)

@pytest.mark.parametrize("q,slug", [("da lat", None), ("dem nhac", None), ("Đêm Nhạc", None)])
def test_accent_insensitive_search(api, q, slug):   # mỗi q trả ≥1 kết quả, mọi kết quả có normalize_vi(title+city+venue+categoryLabel) chứa từng từ
def test_normalize_vi_matches_js():                 # "Đêm Nhạc  Đà Lạt" → "dem nhac da lat"
def test_filter_by_category_and_city(api)
def test_limit_validation_400(api):
    assert api.get("/api/events?limit=0").json() == {"error": "Dữ liệu gửi lên không hợp lệ"}
def test_inactive_and_unapproved_events_excluded(api, api_db)
def test_organizer_events_newest_reviewed_first(api, api_db)   # 2 sự kiện BTC approved với reviewed_at khác nhau
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.**
- [ ] **Step 5:** Thêm Postman "Tìm kiếm" (`/events?q=da lat`). **Commit** `feat(api): danh sách & tìm kiếm sự kiện (không dấu)`.

---

### Task 6: Trang chủ `GET /api/home` + sơ đồ `GET /api/maps/{id}`

**Files:**
- Create: `backend/tests/test_api_home_maps.py`, `backend/seed/dump_legacy_maps.mjs`, `backend/tests/fixtures/legacy_maps.json` (sinh ra, commit)
- Modify: `services/catalog.py`, `routers/catalog.py`, `schemas/catalog.py`, Postman, `backend/README.md` (bảng API giai đoạn 2)

**Interfaces:**
- Produces:
  - `services.catalog.home_sections(db) -> dict[str, list[HomeCard]]`. `HomeCard = EventCard + meta: dict`. Đủ 9 khu theo `HOME_SECTIONS` (khu rỗng trả `[]`), mỗi khu xếp theo `position`, bỏ slot có sự kiện không công khai.
  - Route `GET /api/home` → `{"sections": {...}}`.
  - `services.catalog.get_map(db, map_id: str) -> dict | None`. Dạng giống object JS cũ, để `ZoneMap`/`SeatMap` dùng thẳng:
    - Sơ đồ khu: `{id, kind, name, viewBox, ...decor, groups: {gid: {label,color,ink,max,perks}}, zones: [{id,label,group,cap,text,shape}]}`.
    - Sơ đồ ghế: `{id, kind, name, ...decor, groups: {...}, seats: [{id,x,y,row,num,section,group,label}]}`.
    - `decor` JSONB được trải ra mức ngoài cùng.
  - Route `GET /api/maps/{id}` → JSON, hoặc 404 "Sơ đồ không tồn tại".
  - `dump_legacy_maps.mjs` ghi `ZONE_MAPS` và `getSeatMap(id)` của các sơ đồ ghế đang dùng, mỗi sơ đồ kèm `id` và `kind`. Bỏ các trường là hàm, bỏ `sections` và `groupOf`. Với nhóm, `max` lấy đúng giá trị gốc (`undefined` thì ghi `null`).

- [ ] **Step 1: Sinh `legacy_maps.json`** (TZ VN).
- [ ] **Step 2: Test thất bại**

```python
def test_home_has_all_sections_in_position_order(api, api_db):
    s = api.get("/api/home").json()["sections"]
    assert set(s) == set(HOME_SECTIONS)
    for name, cards in s.items():
        expected = [x["slug"] for x in CAT["homeSlots"] if x["section"] == name]
        assert [c["slug"] for c in cards] == expected
def test_home_cards_carry_meta(api):            # trending[0].meta == {"rank": 1, "num": "text-mustard"}
def test_home_skips_inactive_event(api, api_db)
@pytest.mark.parametrize("legacy", LEGACY_MAPS, ids=lambda m: m["id"])
def test_map_matches_legacy(api, legacy):
    assert api.get(f"/api/maps/{legacy['id']}").json() == legacy   # dump ghi kèm id và kind
def test_unknown_map_404(api)
```
- [ ] **Step 3: FAIL** → **Step 4: cài đặt** → **Step 5: PASS toàn bộ.**
- [ ] **Step 6:** Postman: thêm "Trang chủ" và "Sơ đồ". README thêm bảng 8 endpoint của giai đoạn 2. Chạy thử bằng tay: `uvicorn` rồi `curl http://localhost:8000/api/home`, mở `/docs` thấy đủ endpoint. **Commit** `feat(api): trang chủ & sơ đồ địa điểm`.

---

## Kết thúc giai đoạn 2
- `$PY -m pytest -p no:cacheprovider` pass toàn bộ, gồm cả 41 test đối chiếu chi tiết và test đối chiếu sơ đồ.
- Postman: thư mục "1 · Danh mục" chạy được hết khi server đang bật và DB dev đã nạp dữ liệu.
- Ghi lại mọi trường lệch so với dữ liệu JS cũ (nếu có) để chuẩn bị giai đoạn 6.
