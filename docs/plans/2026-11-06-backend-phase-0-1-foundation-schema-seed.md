# Backend giai đoạn 0–1: Nền móng, Lược đồ, Nạp danh mục — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Có một server FastAPI kết nối PostgreSQL 18, lược đồ đầy đủ (Alembic) và toàn bộ danh mục sự kiện hiện tại được nạp vào DB, kiểm chứng bằng pytest và xem được ERD trong pgAdmin4.

**Architecture:** Thư mục mới `ticketnhip/backend/` chạy song song với `server/` (Node) và không đụng tới nó. Danh mục được xuất **một lần** từ code JS hiện có (`export_catalog.mjs` → `catalog.json`), sau đó `python -m app.seed` upsert vào PostgreSQL qua SQLAlchemy 2.0 ORM (đồng bộ). Lược đồ do Alembic quản lý. VIEW và COMMENT tạo bằng `op.execute`.

**Tech Stack:** Python 3.14, FastAPI 0.143, SQLAlchemy ≥ 2.0.36, psycopg 3 (`psycopg[binary]`), Alembic, pydantic-settings, pytest; Node ≥ 22.13 (chỉ dùng cho script export); PostgreSQL 18 + pgAdmin 4.

**Spec:** `ticketnhip/docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 4, 5, 6-cấu trúc, 7-giai đoạn 0–1, 8, 9). Giai đoạn 2–7 sẽ có kế hoạch riêng.

## Global Constraints

- Không sửa gì trong `server/` hay `src/` ở kế hoạch này. Node cũ phải chạy được như trước (`npm run dev`).
- Đường dẫn dự án có "Tài liệu" dạng **NFD**. Trong Bash luôn `cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip` (glob). Sau khi tạo file bằng Write/Edit, chạy `ls -d /c/Users/khact/OneDrive/T*/`: chỉ được có **một** thư mục "Tài liệu".
- Thời gian: `timestamptz`. Múi giờ hiển thị và quy đổi ngày là `Asia/Ho_Chi_Minh`. Tiền: `integer` VND.
- DB `ticketnhip` (dev) và `ticketnhip_test` (pytest), `ENCODING 'UTF8'`, chủ sở hữu là role `ticketnhip` / mật khẩu `ticketnhip` (chỉ dùng khi phát triển).
- `DATABASE_URL=postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip`, `TEST_DATABASE_URL` tương tự với `ticketnhip_test`. Đọc từ `backend/.env`. Không commit file này, có `backend/.env.example`.
- Mọi thông báo lỗi gửi người dùng bằng tiếng Việt, dạng JSON `{"error": "..."}`.
- Lệnh Python luôn dùng venv: `backend/.venv/Scripts/python.exe` (viết tắt `$PY` trong kế hoạch: `PY=backend/.venv/Scripts/python.exe`).
- `catalog.json` được commit và là nguồn nạp chính thức.
- Mỗi bảng và VIEW có `COMMENT ON` tiếng Việt.

## Review Focus

1. **Chạy lại seed sau khi đã có bán vé thật** không được làm mất hay đặt lại `tier_stock.sold`, `seat_holds` có `order_id`, đơn hàng, hay đổi `events.id`. Test thuộc Task 6.
2. **Chữ tiếng Việt có dấu** phải giữ nguyên sau khi nạp và đọc lại (ví dụ "Concert Đêm 4: Hẹn Giữa Tinh Hà", "Nhạc kịch “Phố Đèn Lồng”" có ngoặc kép cong). Test thuộc Task 6.
3. **Giờ suất diễn**: 19:30 giờ VN phải lưu đúng thời điểm 12:30Z, và `shows.id` = `YYYYMMDD-1930`. Test thuộc Task 6.
4. **Chạy export trên máy không đặt TZ=Asia/Ho_Chi_Minh** sẽ cho mã suất diễn sai. Script phải từ chối chạy (exit code 1, có thông báo). Test thuộc Task 5.
5. **PostgreSQL chưa chạy hoặc `DATABASE_URL` sai** thì `/api/health` phải trả 503 `{"error": "Không kết nối được CSDL…"}`, không được ném stack trace. Test thuộc Task 1.

---

## File Structure

```
ticketnhip/
  .gitignore                         # Task 1 (node_modules, dist, .data, backend/.venv, backend/.env, __pycache__)
  backend/
    requirements.txt  .env.example  README.md
    pytest.ini                       # testpaths=tests
    alembic.ini
    alembic/env.py                   # đọc DATABASE_URL từ config, target_metadata = Base.metadata
    alembic/versions/0001_initial.py # Task 2–4: bảng; Task 7: VIEW + COMMENT (migration 0002)
    scripts/create_db.sql            # Task 1: role + 2 DB
    scripts/export_schema.sh         # Task 7: pg_dump --schema-only → schema.sql
    schema.sql                       # Task 7 (sinh ra, commit)
    app/
      __init__.py
      config.py                      # Settings
      db.py                          # engine, SessionLocal, get_db, Base
      main.py                        # FastAPI app, /api/health, xử lý lỗi
      models/__init__.py             # import mọi model để Alembic thấy
      models/catalog.py              # Task 2
      models/users.py                # Task 3
      models/sales.py                # Task 4
      security.py                    # Task 6: hash_password / verify_password (scrypt, tương thích Node)
      seed.py                        # Task 6
    seed/
      export_catalog.mjs             # Task 5
      catalog.json                   # Task 5 (sinh ra, commit)
    tests/
      conftest.py                    # Task 1–2: engine test, migrate head, session rollback
      test_health.py  test_schema_catalog.py  test_schema_users.py  test_schema_sales.py
      test_catalog_json.py  test_security.py  test_seed.py  test_views.py
```

---

### Task 1: Git, khung `backend/`, kết nối DB, `/api/health`

**Files:**
- Create: `.gitignore`, `backend/requirements.txt`, `backend/.env.example`, `backend/.env`, `backend/pytest.ini`, `backend/scripts/create_db.sql`, `backend/app/{__init__,config,db,main}.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`, `backend/README.md`

**Interfaces:**
- Produces:
  - `app.config.settings: Settings` có `database_url: str`, `test_database_url: str`, `env: Literal['dev','prod'] = 'dev'`, `admin_email: str = 'admin@ticketnhip.vn'`, `admin_password: str | None = None`.
  - `app.db.Base` (DeclarativeBase), `app.db.make_engine(url: str) -> Engine` (`echo=settings.env == 'dev'`, `pool_pre_ping=True`), `app.db.engine`, `app.db.SessionLocal`, `app.db.get_db() -> Iterator[Session]`.
  - `app.main.app: FastAPI`, các router gắn dưới tiền tố `/api`.
  - Fixture pytest `engine` (session-scope, dùng `TEST_DATABASE_URL`) và `client` (`TestClient(app)` với `get_db` override sang engine test).

- [ ] **Step 1: Khởi tạo git và `.gitignore`**

```bash
cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip && git init && git add -A && git commit -m "chore: snapshot dự án trước khi dựng backend FastAPI"
```
Nội dung `.gitignore`: `node_modules/`, `dist/`, `.data/`, `backend/.venv/`, `backend/.env`, `__pycache__/`, `.pytest_cache/`. Lệnh `git status` sau commit phải sạch, và `.data/ticketnhip.db` không được nằm trong commit.

- [ ] **Step 2: Tạo role và DB**

`backend/scripts/create_db.sql`:
```sql
CREATE ROLE ticketnhip LOGIN PASSWORD 'ticketnhip';
CREATE DATABASE ticketnhip OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE ticketnhip_test OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
```
Người dùng chạy (cần mật khẩu `postgres`): `"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -f backend/scripts/create_db.sql`. Cách khác là mở pgAdmin → Query Tool → dán file này. Kiểm tra: `"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U ticketnhip -d ticketnhip -c "select version()"` in ra `PostgreSQL 18`.

- [ ] **Step 3: venv và thư viện**

`requirements.txt`: `fastapi[standard]>=0.143`, `sqlalchemy>=2.0.36`, `psycopg[binary]>=3.2`, `alembic>=1.14`, `pydantic-settings>=2.6`, `pytest>=8`.
```bash
cd backend && python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt && .venv/Scripts/python.exe -c "import psycopg, sqlalchemy; print(psycopg.__version__, sqlalchemy.__version__)"
```
Nếu `psycopg[binary]` chưa có wheel cho Python 3.14, đổi sang `psycopg>=3.2` (bản thuần Python) và thêm `C:\Program Files\PostgreSQL\18\bin` vào PATH của phiên làm việc để nạp `libpq`. Ghi lại cách này trong README.

- [ ] **Step 4: Viết test thất bại** `tests/test_health.py`

```python
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
```
Fixture `client_bad_db` override `get_db` bằng engine trỏ tới `postgresql+psycopg://ticketnhip:sai@localhost:5432/ticketnhip`.

- [ ] **Step 5: Chạy, phải FAIL**: `$PY -m pytest tests/test_health.py -v` → lỗi import `app.main` hoặc 404.

- [ ] **Step 6: Cài đặt** `config.py`, `db.py`, `main.py`

- `GET /api/health` chạy `SHOW server_version` và trả `{"ok": True, "postgres": <chuỗi>}`.
- Exception handler cho `sqlalchemy.exc.OperationalError` trả 503 kèm câu tiếng Việt ở trên.
- Exception handler cho `HTTPException` trả `{"error": detail}`, để giữ đúng dạng lỗi của API Node.

- [ ] **Step 7: Chạy, phải PASS**: `$PY -m pytest -v` → 2 passed.

- [ ] **Step 8: README + commit**

README gồm: tạo DB (Step 2), tạo venv, `.env`, cách chạy `uvicorn app.main:app --reload --port 8000`, mở `http://localhost:8000/docs`.

Tạo thêm `backend/postman/ticketnhip.postman_collection.json` (Postman v2.1) với biến `baseUrl = http://localhost:8000/api`, thư mục "0 · Hệ thống" chứa request `GET {{baseUrl}}/health`. Request này có test script `pm.response.to.have.status(200)`. Các giai đoạn sau sẽ thêm thư mục vào cùng file. Thử bằng cách import vào Postman, chạy request, thấy status 200.
```bash
git add .gitignore backend && git commit -m "feat(backend): khung FastAPI + kết nối PostgreSQL + /api/health"
```

---

### Task 2: Model danh mục + Alembic + migration đầu tiên

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`, `backend/app/models/{__init__,catalog}.py`, `backend/tests/test_schema_catalog.py`
- Modify: `backend/tests/conftest.py` (trước khi chạy test: `alembic downgrade base` rồi `upgrade head` trên DB test; fixture `db` mở connection + transaction, rollback sau mỗi test)

**Interfaces:**
- Consumes: `app.db.Base`, `settings.test_database_url`.
- Produces (class trong `app.models.catalog`, tên bảng trong ngoặc). Cột theo spec mục 4, cộng các điểm cụ thể sau:
  - `Category` (`categories`): `id: str` PK, `label`, `dot`, `sort_order: int`.
  - `VenueMap` (`venue_maps`): `id: str` PK, `kind` CHECK `in ('zones','seats')`, `name`, `view_box: str | None`, `decor: dict` (JSONB, giữ mọi trường hiển thị còn lại của sơ đồ: `decor`, `stage`, `labels`, `rowLabels`, `width`, `height`, `pitch`, `radius`).
  - `MapGroup` (`map_groups`): PK `(map_id, id)`, `label`, `color`, `ink: bool = False`, `max_per_order: int | None` CHECK `> 0`, `perks`.
  - `MapZone` (`map_zones`): PK `(map_id, id)`, `label`, `group_id`, `capacity` CHECK `> 0`, `shape: dict` JSONB, `text: list` JSONB, FK `(map_id, group_id)` → `map_groups`.
  - `MapSeat` (`map_seats`): PK `(map_id, id)`, `section`, `row_label`, `num: int`, `group_id`, `label`, `x: float`, `y: float`, FK nhóm.
  - `Event` (`events`):
    - Cột: `id` serial PK, `slug` UNIQUE, `title`, `search_text` (chữ thường, đã bỏ dấu), `category_id` FK, `city`, `venue`, `address`, `layout` CHECK `in ('list','zones','seats')`, `map_id` FK NULL, `organizer_id: int | None` (ở Task 2 chỉ là cột số. Task 3 thêm `ForeignKey('organizers.user_id', ondelete='CASCADE')` khi đã có bảng `organizers`), `host_name`, `host_bio`, `description: list[str]` (ARRAY Text), `notes: list[str]`, `status` CHECK `in ('pending','approved','rejected')` default `'approved'`, `reject_reason`, `sale_start` timestamptz NULL, `resale_count` int default 0, `created_at` default `now()`, `reviewed_at` NULL.
    - CHECK `ck_events_layout_map`: `(layout = 'list') = (map_id IS NULL)`.
  - `Show` (`shows`): PK `(event_id, id)`, `starts_at` timestamptz, `end_time: time`.
  - `TicketTier` (`ticket_tiers`): PK `(event_id, id)`, `name`, `price` CHECK `>= 0`, `capacity` CHECK `>= 0`, `max_per_order` CHECK `> 0`, `perks`, `group_id` NULL, `sort_order`.
  - `HomeSlot` (`home_slots`): PK `(section, position)`, `event_id` FK, `meta: dict` JSONB default `{}`. CHECK `section in ('hero','featured-upcoming','featured-new','trending','posters','resale','schedule-weekend','schedule-month','catalog')`.
  - Khoá ngoại tới `events` đều `ON DELETE CASCADE`.

Vì bảng `events` tham chiếu tới `organizers`, migration `0001_initial` được sinh **một lần sau Task 4** (`alembic revision --autogenerate`). Ở Task 2–3, test chạy trên `Base.metadata.create_all` của DB test. Task 4 đổi conftest sang `alembic upgrade head`.

- [ ] **Step 1: Viết test thất bại** `tests/test_schema_catalog.py`

```python
def test_list_event_cannot_have_map(db, make_category):
    db.add(Event(slug="x", title="X", search_text="x", category_id=make_category.id, city="Hà Nội",
                 venue="V", address="A", layout="list", map_id="arena", description=[], notes=[]))
    with pytest.raises(IntegrityError, match="ck_events_layout_map"):
        db.flush()

def test_zone_capacity_must_be_positive(db, make_map):  # make_map tạo VenueMap zones + MapGroup 'vip'
    db.add(MapZone(map_id=make_map.id, id="z", label="Z", group_id="vip", capacity=0, shape={}, text=[]))
    with pytest.raises(IntegrityError): db.flush()

def test_event_slug_unique(db, make_event):
    db.add(Event(**{**make_event.as_dict(), "id": None}))
    with pytest.raises(IntegrityError, match="slug"): db.flush()

def test_home_slot_rejects_unknown_section(db, make_event):
    db.add(HomeSlot(section="banner", position=1, event_id=make_event.id, meta={}))
    with pytest.raises(IntegrityError): db.flush()
```
Các fixture factory nhỏ (`make_category`, `make_map`, `make_event`) đặt trong conftest. `as_dict()` là một helper trong test, không nằm trong model.

- [ ] **Step 2: Chạy, phải FAIL**: `$PY -m pytest tests/test_schema_catalog.py -v` → ImportError.
- [ ] **Step 3: Viết các model** ở `app/models/catalog.py` (theo Interfaces) và `app/models/__init__.py` import tất cả. Cài Alembic: `alembic init alembic`, rồi trong `env.py` đặt `target_metadata = Base.metadata` và `url = settings.database_url` (cho phép ghi đè bằng `-x url=`).
- [ ] **Step 4: Chạy, phải PASS**: 4 passed.
- [ ] **Step 5: Commit**: `git commit -am "feat(backend): model danh mục sự kiện, sơ đồ, suất diễn, hạng vé"` (thêm file mới bằng `git add backend`).

---

### Task 3: Model người dùng, phiên, Ban tổ chức

**Files:**
- Create: `backend/app/models/users.py`, `backend/tests/test_schema_users.py`
- Modify: `backend/app/models/catalog.py` (thêm FK cho `Event.organizer_id`)

**Interfaces:**
- Produces:
  - `User` (`users`): `id` serial, `name`, `email` UNIQUE NULL, `phone` UNIQUE NULL, `password_hash`, `role` CHECK `in ('customer','organizer','admin')` default `'customer'`, `created_at`. CHECK `ck_users_contact`: `email IS NOT NULL OR phone IS NOT NULL`.
  - `Session` (`sessions`): `token_hash` PK, `user_id` FK CASCADE, `expires_at` timestamptz. Tên class Python là `UserSession`, để tránh trùng với `sqlalchemy.orm.Session`.
  - `PasswordReset` (`password_resets`): `token_hash` PK, `user_id` FK CASCADE, `expires_at`, `used: bool = False`.
  - `Organizer` (`organizers`): `user_id` PK FK CASCADE, `org_name`, `phone`, `description` NULL, `created_at`.

- [ ] **Step 1: Test thất bại**

```python
def test_user_needs_email_or_phone(db):
    db.add(User(name="A", password_hash="h"))
    with pytest.raises(IntegrityError, match="ck_users_contact"): db.flush()

def test_role_is_restricted(db):
    db.add(User(name="A", email="a@x.vn", password_hash="h", role="root"))
    with pytest.raises(IntegrityError): db.flush()

def test_deleting_user_cascades_sessions_and_organizer(db):
    u = User(name="A", email="a@x.vn", password_hash="h"); db.add(u); db.flush()
    db.add_all([UserSession(token_hash="t", user_id=u.id, expires_at=now_plus(days=1)),
                Organizer(user_id=u.id, org_name="Org", phone="0912345678")]); db.flush()
    db.delete(u); db.flush()
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    assert db.scalar(select(func.count()).select_from(Organizer)) == 0
```
- [ ] **Step 2: FAIL** → **Step 3: viết model** → **Step 4: PASS** (`$PY -m pytest tests/test_schema_users.py -v`, 3 passed. Chạy cả bộ test thì Task 2 vẫn pass).
- [ ] **Step 5: Commit** `feat(backend): model người dùng, phiên, ban tổ chức`.

---

### Task 4: Model bán vé, kho vé + migration `0001_initial`

**Files:**
- Create: `backend/app/models/sales.py`, `backend/alembic/versions/0001_initial.py` (autogenerate rồi đọc lại), `backend/tests/test_schema_sales.py`
- Modify: `backend/tests/conftest.py` (bỏ `create_all`, thay bằng `alembic downgrade base && upgrade head` qua API `alembic.command`, với `-x url=TEST_DATABASE_URL`)

**Interfaces:**
- Produces:
  - `Coupon` (`coupons`): `code` PK, `amount` CHECK `> 0`, `min_order` CHECK `>= 0`, `active: bool = True`.
  - `TierStock` (`tier_stock`): PK `(event_id, show_id, tier_id)`, `capacity`, `presold` default 0, `sold` default 0. CHECK `presold >= 0 AND sold >= 0`, CHECK `ck_tier_stock_capacity`: `presold + sold <= capacity`. FK `(event_id, show_id)` → `shows`, FK `(event_id, tier_id)` → `ticket_tiers`.
  - `SeatHold` (`seat_holds`): PK `(event_id, show_id, seat_id)`, `order_id` FK NULL CASCADE. FK `(event_id, show_id)` → `shows`.
  - `Order` (`orders`):
    - Cột: `id: str` PK, `user_id` FK CASCADE, `event_id`, `show_id`, `subtotal`, `discount` default 0, `coupon_code` FK NULL, `total`, `method` CHECK `in ('qr','wallet','card')`, `buyer_name`, `buyer_email`, `buyer_phone`, `status` CHECK `in ('paid','refunded','cancelled')` default `'paid'`, `created_at`.
    - FK `(event_id, show_id)` → `shows`. CHECK `ck_orders_total`: `total = subtotal - discount AND discount >= 0 AND total >= 0`.
    - Index `(user_id)`, `(event_id, created_at)`.
  - `OrderItem` (`order_items`): PK `(order_id, tier_id)`, `event_id`, `price` CHECK `>= 0`, `qty` CHECK `> 0`. FK `(event_id, tier_id)` → `ticket_tiers`.
  - `Ticket` (`tickets`): `code` PK, `order_id` FK CASCADE, `event_id`, `tier_id`, `price`, `seat_id` NULL, `checked_in_at` NULL. FK `(event_id, tier_id)` → `ticket_tiers`. Index `(order_id)`.

- [ ] **Step 1: Test thất bại** `tests/test_schema_sales.py` (fixture `make_show_tier` tạo event + show + tier capacity 10)

```python
def test_stock_cannot_exceed_capacity(db, make_show_tier):
    e, s, t = make_show_tier
    db.add(TierStock(event_id=e.id, show_id=s.id, tier_id=t.id, capacity=10, presold=6, sold=5))
    with pytest.raises(IntegrityError, match="ck_tier_stock_capacity"): db.flush()

def test_same_seat_cannot_be_held_twice(db, make_show_tier):
    e, s, _ = make_show_tier
    db.add(SeatHold(event_id=e.id, show_id=s.id, seat_id="G-A1")); db.flush()
    db.add(SeatHold(event_id=e.id, show_id=s.id, seat_id="G-A1"))
    with pytest.raises(IntegrityError): db.flush()

def test_order_total_must_equal_subtotal_minus_discount(db, make_show_tier, make_user):
    e, s, _ = make_show_tier
    db.add(Order(id="TN-AAAAAAA", user_id=make_user.id, event_id=e.id, show_id=s.id, subtotal=600000,
                 discount=50000, total=600000, method="qr", buyer_name="B", buyer_email="b@x.vn", buyer_phone="0912345678"))
    with pytest.raises(IntegrityError, match="ck_orders_total"): db.flush()

def test_order_item_must_reference_existing_tier(db, make_order):
    db.add(OrderItem(order_id=make_order.id, event_id=make_order.event_id, tier_id="khong-co", price=1, qty=1))
    with pytest.raises(IntegrityError): db.flush()
```
- [ ] **Step 2: FAIL** → **Step 3: viết model + sinh migration**: `cd backend && .venv/Scripts/alembic.exe revision --autogenerate -m initial --rev-id 0001`. Đọc lại file và sửa nếu autogenerate bỏ sót CHECK hoặc FK ghép. Cập nhật conftest.
- [ ] **Step 4: PASS toàn bộ**: `$PY -m pytest -v` (Task 1–4 đều pass trên DB dựng bằng migration). Chạy thêm `.venv/Scripts/alembic.exe upgrade head` trên DB dev, mở pgAdmin → `ticketnhip` → Schemas → Tables, phải có 19 bảng (`categories, venue_maps, map_groups, map_zones, map_seats, events, shows, ticket_tiers, home_slots, users, sessions, password_resets, organizers, coupons, tier_stock, seat_holds, orders, order_items, tickets`).
- [ ] **Step 5: Commit** `feat(backend): model bán vé + kho vé + migration 0001_initial`.

---

### Task 5: Xuất danh mục từ JS → `catalog.json`

**Files:**
- Create: `backend/seed/export_catalog.mjs`, `backend/seed/catalog.json` (sinh ra), `backend/tests/test_catalog_json.py`

**Interfaces:**
- Consumes (chỉ import, không sửa): `src/lib/events.js` (`events`, `showIdOf`), `src/lib/seating.js` (`presoldZone`, `isSeatPresold`), `src/data/venueMaps.js` (`ZONE_MAPS`, `getSeatMap`), `src/data/navigation.js` (`categories`), `src/data/hero.js`, `src/data/home.js`, `src/data/discover.js`, `src/data/rules.js` (`COUPONS`), `src/lib/utils.js` (`normalizeVi`).
- Produces: `catalog.json` dạng
```json
{ "version": 1, "generatedAt": "...",
  "categories": [{ "id", "label", "dot", "sortOrder" }],
  "maps": [{ "id", "kind": "zones|seats", "name", "viewBox", "display": {...},
             "groups": [{ "id", "label", "color", "ink", "maxPerOrder", "perks" }],
             "zones": [{ "id", "label", "groupId", "capacity", "shape", "text" }],
             "seats": [{ "id", "section", "row", "num", "groupId", "label", "x", "y" }] }],
  "events": [{ "slug", "title", "searchText", "categoryId", "city", "venue", "address", "layout", "mapId",
               "hostName", "hostBio", "description": [], "notes": [], "saleStart": "ISO|null", "resaleCount",
               "shows": [{ "id", "startsAt": "ISO+07:00", "endTime": "HH:MM" }],
               "tiers": [{ "id", "name", "price", "capacity", "maxPerOrder", "perks", "groupId", "sortOrder" }],
               "presold": [{ "showId", "tierId", "qty" }],
               "presoldSeats": [{ "showId", "seatId" }] }],
  "homeSlots": [{ "section", "position", "slug", "meta": {} }],
  "coupons": [{ "code", "amount", "minOrder" }] }
```
  - Quy tắc dữ liệu:
    - `capacity` của hạng `list` lấy `remaining` hiện tại, và không có `presold`.
    - Hạng `zones`: mỗi show × zone có `presold = presoldZone(slug, showId, zoneId, cap)`.
    - Hạng `seats`: `presoldSeats` gồm mọi ghế có `isSeatPresold(...)` là true. `tiers[].capacity` = số ghế của nhóm.
    - `saleStart` = `saleOpensAt` khi `status === 'coming'`, ngược lại là `null`.
    - `hostName/hostBio` lấy từ `organizer.name/bio`.
    - `searchText` = `normalizeVi(\`${title} ${city} ${venue} ${categoryLabel}\`)`.
  - Gộp alias: `const ALIASES = { 'concert-dem-4-tinh-ha': 'concert-dem-4-hen-giua-tinh-ha' }`. Sự kiện có slug là alias bị bỏ khỏi `events`, mọi slot trỏ về slug chuẩn.
  - `homeSlots` theo thứ tự xuất hiện trong mảng nguồn, `position` bắt đầu từ 1. `meta` chỉ chứa phần trang trí:
    - `hero`: `{no}`
    - `featured-upcoming`, `featured-new`: `{}`
    - `trending`: `{rank, num}`
    - `posters`: `{tag, tilt}`
    - `resale`: `{line}`
    - `schedule-weekend`, `schedule-month`: `{}`
    - `catalog`: `{cityId}`
  - Script in ra stdout bảng **"Thẻ thay đổi so với hiện tại"**: mỗi slot có ngày `dd.MM`, giờ, hoặc giá (nghìn) trên thẻ cũ khác với dữ liệu sự kiện (show đầu tiên, `minPrice/1000`), cộng mỗi alias đã gộp.

- [ ] **Step 1: Test thất bại** `tests/test_catalog_json.py`

```python
CAT = json.loads((ROOT / "seed/catalog.json").read_text(encoding="utf-8"))

def test_every_event_has_show_and_tier():
    assert all(e["shows"] and e["tiers"] for e in CAT["events"])

def test_slugs_unique_and_alias_merged():
    slugs = [e["slug"] for e in CAT["events"]]
    assert len(slugs) == len(set(slugs))
    assert "concert-dem-4-tinh-ha" not in slugs
    assert "concert-dem-4-hen-giua-tinh-ha" in slugs

def test_home_slots_point_to_existing_events():
    slugs = {e["slug"] for e in CAT["events"]}
    assert all(s["slug"] in slugs for s in CAT["homeSlots"])

def test_show_ids_are_vietnam_local_time():
    ev = next(e for e in CAT["events"] if e["slug"] == "concert-dem-4-hen-giua-tinh-ha")
    s = ev["shows"][0]
    assert s["startsAt"].endswith("+07:00")
    assert s["id"] == s["startsAt"][:10].replace("-", "") + "-" + s["startsAt"][11:16].replace(":", "")

def test_zone_presold_within_capacity():
    for e in CAT["events"]:
        cap = {t["id"]: t["capacity"] for t in e["tiers"]}
        assert all(0 <= p["qty"] <= cap[p["tierId"]] for p in e["presold"])

def test_export_refuses_wrong_timezone():
    r = subprocess.run(["node", "backend/seed/export_catalog.mjs", "--check-only"], cwd=PROJECT,
                       env={**os.environ, "TZ": "UTC"}, capture_output=True, text=True)
    assert r.returncode == 1 and "TZ=Asia/Ho_Chi_Minh" in r.stderr
```
- [ ] **Step 2: FAIL** (chưa có file).
- [ ] **Step 3: Viết `export_catalog.mjs`**
  - Kiểm tra múi giờ trước khi làm gì khác: nếu `Intl.DateTimeFormat().resolvedOptions().timeZone !== 'Asia/Ho_Chi_Minh'` thì `console.error('Hãy chạy với TZ=Asia/Ho_Chi_Minh …')` và `process.exit(1)`.
  - `--check-only` chỉ kiểm tra múi giờ rồi thoát với mã 0.
  - Ghi `startsAt` dạng `YYYY-MM-DDTHH:mm:00+07:00`, dựng từ giờ máy (không dùng `toISOString`).
  - Xử lý thẻ trang chủ: tra slug bằng `slugify(title)`, áp `ALIASES`.
  - Script import file ở `src/` bằng đường dẫn tương đối `../../src/...`, nên phải chạy từ gốc dự án.
- [ ] **Step 4: Chạy export rồi test**
```bash
cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip && TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs > /tmp/changes.txt; cat /tmp/changes.txt
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_json.py -v
```
Kết quả mong đợi: 6 passed. Bảng "Thẻ thay đổi" có ít nhất dòng "Show thực cảnh: Cờ Lau" (CN 08.11 → 06.11) và dòng gộp alias. Dán bảng này vào báo cáo cuối task để người dùng xem lại.
- [ ] **Step 5: Commit** `feat(seed): xuất danh mục sự kiện từ JS ra catalog.json`.

---

### Task 6: Băm mật khẩu + `python -m app.seed`

**Files:**
- Create: `backend/app/security.py`, `backend/app/seed.py`, `backend/tests/test_security.py`, `backend/tests/test_seed.py`

**Interfaces:**
- Consumes: các model ở Task 2–4, `catalog.json` từ Task 5, `settings.admin_email/admin_password/env`.
- Produces:
  - `app.security.hash_password(pw: str) -> str`: định dạng `scrypt$<salt b64>$<key b64>`, salt 16 byte, `hashlib.scrypt(n=16384, r=8, p=1, dklen=64)`. Các tham số này là mặc định của Node, nên hash tạo bằng Node vẫn kiểm tra được.
  - `app.security.verify_password(pw: str, stored: str) -> bool` (dùng `hmac.compare_digest`).
  - `app.seed.load_catalog(db: Session, catalog: dict) -> SeedReport` (`SeedReport` là dataclass đếm `events, shows, tiers, seats, slots`).
  - `app.seed.reset_all(db: Session) -> None`.
  - `app.seed.ensure_admin(db: Session) -> None`.
  - CLI: `python -m app.seed [--reset]`.

- [ ] **Step 1: Test thất bại** `tests/test_security.py`

```python
NODE_HASH = "<dán kết quả lệnh bên dưới>"
# cd ticketnhip && node -e "import('./server/auth.js').then(async m => console.log(await m.hashPassword('admin123456')))"
def test_verifies_hash_made_by_node():
    assert verify_password("admin123456", NODE_HASH)
    assert not verify_password("sai-mat-khau", NODE_HASH)

def test_round_trip_and_format():
    h = hash_password("matkhau123")
    assert h.startswith("scrypt$") and verify_password("matkhau123", h)
```
Lệnh `node -e` import `server/auth.js`, file này lại import `db.js` và sẽ mở file SQLite (vô hại, vì chỉ đọc hoặc tạo `.data`). Nếu lệnh lỗi, chép riêng hàm `hashPassword` (dòng 13–17 của `server/auth.js`) vào một lệnh `node -e` độc lập.

- [ ] **Step 2: FAIL** → **Step 3: viết `security.py`** → **Step 4: PASS** → commit `feat(backend): băm mật khẩu scrypt tương thích Node`.

- [ ] **Step 5: Test thất bại** `tests/test_seed.py` (fixture `seeded`: `reset_all` + `load_catalog` với `catalog.json` thật trên DB test)

```python
def test_counts_match_catalog(seeded, db):
    assert db.scalar(select(func.count()).select_from(Event)) == len(CAT["events"])
    assert db.scalar(select(func.count()).select_from(HomeSlot)) == len(CAT["homeSlots"])
    assert db.scalar(select(func.count()).select_from(MapSeat)) == sum(len(m["seats"]) for m in CAT["maps"])

def test_vietnamese_text_round_trips(seeded, db):
    titles = set(db.scalars(select(Event.title)))
    assert "Concert Đêm 4: Hẹn Giữa Tinh Hà" in titles
    assert "Nhạc kịch “Phố Đèn Lồng”" in titles

def test_show_time_is_stored_as_correct_instant(seeded, db):
    s = db.scalars(select(Show).join(Event).where(Event.slug == "concert-dem-4-hen-giua-tinh-ha")).first()
    local = s.starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    assert s.id == local.strftime("%Y%m%d-%H%M")

def test_reseed_preserves_ids_and_real_sales(seeded, db):
    ev = db.scalar(select(Event).where(Event.slug == "concert-dem-4-hen-giua-tinh-ha"))
    stock = db.scalars(select(TierStock).where(TierStock.event_id == ev.id)).first()
    stock.sold = 3
    org_ev = make_org_event(db)            # helper: user + organizer + event organizer_id != NULL
    db.commit()
    load_catalog(db, CAT); db.commit()
    assert db.scalar(select(Event.id).where(Event.slug == ev.slug)) == ev.id
    assert db.get(TierStock, (stock.event_id, stock.show_id, stock.tier_id)).sold == 3
    assert db.get(Event, org_ev.id) is not None

def test_sale_start_loaded_for_coming_events(seeded, db):
    coming = [e for e in CAT["events"] if e["saleStart"]]
    assert coming, "catalog phải có sự kiện sắp mở bán"
    ev = db.scalar(select(Event).where(Event.slug == coming[0]["slug"]))
    assert ev.sale_start is not None

def test_reset_all_empties_everything(seeded, db):
    reset_all(db); db.commit()
    assert db.scalar(select(func.count()).select_from(Event)) == 0

def test_admin_created_once(db):
    ensure_admin(db); ensure_admin(db); db.commit()
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) == 1
```
Test `test_reseed_preserves_ids_and_real_sales` và `test_reset_all_empties_everything` phải commit thật. Vì vậy fixture `seeded` của file này **không** dùng transaction rollback, mà gọi `reset_all` ở đầu mỗi test.

- [ ] **Step 6: FAIL** → **Step 7: viết `seed.py`**
  - **Upsert:** dùng `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update` theo khoá tự nhiên.
    - `events` theo `slug`, chỉ với sự kiện có `organizer_id IS NULL`.
    - `shows`, `ticket_tiers`, `map_*`, `home_slots`, `coupons` theo PK.
    - `tier_stock`: chỉ cập nhật `capacity` và `presold`, **không** ghi đè `sold`.
    - `seat_holds` đã bán sẵn: chèn với `on_conflict_do_nothing`, và chỉ xoá những dòng có `order_id IS NULL` không còn trong catalog.
  - **Dòng thừa:** show, tier hay slot không còn trong catalog thì xoá, nhưng chỉ khi không có đơn hàng tham chiếu. Nếu có thì giữ lại và in cảnh báo.
  - **`reset_all`:** `TRUNCATE ... RESTART IDENTITY CASCADE` mọi bảng.
  - **`ensure_admin`:** giống `seedAdmin` cũ. Khi `env='prod'` mà không có `ADMIN_PASSWORD` thì in cảnh báo và bỏ qua. Khi dev, mật khẩu mặc định là `admin123456`.
  - **`__main__`:** đọc `seed/catalog.json`, gọi các hàm trên, commit, in `SeedReport`.
- [ ] **Step 8: PASS**: `$PY -m pytest -v` (toàn bộ). Sau đó nạp vào DB dev: `cd backend && .venv/Scripts/python.exe -m app.seed`. Lệnh in số sự kiện, show, hạng vé, ghế, slot, và các số này phải khớp `catalog.json`. Chạy lần thứ hai cho ra cùng các con số.
- [ ] **Step 9: Commit** `feat(seed): nạp danh mục vào PostgreSQL (upsert, --reset, admin)`.

---

### Task 7: VIEW thống kê, COMMENT, `schema.sql`, ERD

**Files:**
- Create: `backend/alembic/versions/0002_views_comments.py`, `backend/scripts/export_schema.sh`, `backend/schema.sql` (sinh ra), `backend/tests/test_views.py`
- Modify: `backend/README.md` (mục "Xem ERD trong pgAdmin")

**Interfaces:**
- Produces (giai đoạn 7 dùng):
  - `v_event_sales(event_id, show_id, tier_id, sold, revenue)`: `sold = SUM(order_items.qty)`, `revenue = SUM(price*qty)`. Chỉ tính đơn có `status = 'paid'`.
  - `v_daily_revenue(organizer_id, day date, revenue, tickets)`: `day = (orders.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date`, `revenue = SUM(orders.total)`, `tickets = SUM(qty)`. Hai tổng này tính bằng truy vấn con riêng, để `total` không bị cộng lặp. Chỉ tính đơn `paid`, gộp theo `events.organizer_id` (NULL = sự kiện của sàn).
  - `COMMENT ON TABLE` cho cả 19 bảng và 2 VIEW, viết tiếng Việt một câu, ví dụ `'Suất diễn của sự kiện; id dạng YYYYMMDD-HHMM'`.

- [ ] **Step 1: Test thất bại** `tests/test_views.py`

```python
def test_daily_revenue_uses_vietnam_day(db, make_order_at):
    make_order_at("2026-11-06T18:30:00Z", total=550000, items=[("ve-1", 600000, 1)], discount=50000)
    row = db.execute(text("select day, revenue, tickets from v_daily_revenue")).one()
    assert str(row.day) == "2026-11-07" and row.revenue == 550000 and row.tickets == 1

def test_daily_revenue_not_doubled_by_multiple_items(db, make_order_at):
    make_order_at("2026-11-06T03:00:00Z", total=900000, items=[("ve-1", 300000, 1), ("ve-2", 600000, 1)])
    row = db.execute(text("select revenue, tickets from v_daily_revenue")).one()
    assert row.revenue == 900000 and row.tickets == 2

def test_every_table_has_comment(db):
    missing = db.execute(text("""select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relkind in ('r','v') and c.relname <> 'alembic_version'
        and obj_description(c.oid) is null""")).scalars().all()
    assert missing == []
```
- [ ] **Step 2: FAIL** → **Step 3: viết migration 0002** (`op.execute` cho `CREATE VIEW` và `COMMENT ON`. `downgrade` thì `DROP VIEW`). Fixture `make_order_at` để trong conftest.
- [ ] **Step 4: PASS** `$PY -m pytest -v`. Sau đó chạy `alembic upgrade head` trên DB dev.
- [ ] **Step 5: Xuất `schema.sql`**: `export_schema.sh` chạy `"/c/Program Files/PostgreSQL/18/bin/pg_dump.exe" --schema-only --no-owner -U ticketnhip ticketnhip > backend/schema.sql`. File sinh ra phải có `CREATE VIEW public.v_daily_revenue` và `COMMENT ON TABLE public.shows`. Ghi vào README cách xem ERD: pgAdmin → chuột phải DB `ticketnhip` → *ERD For Database*.
- [ ] **Step 6: Commit** `feat(db): VIEW thống kê, chú thích bảng, schema.sql`.

---

## Kết thúc giai đoạn 0–1 (kiểm tra cuối)

- `$PY -m pytest -v` pass toàn bộ. `npm run dev` (Node cũ) vẫn chạy được trang chủ.
- pgAdmin hiển thị 19 bảng + 2 VIEW có chú thích, và ERD vẽ được.
- Báo lại người dùng: bảng "Thẻ thay đổi so với hiện tại" (Task 5), các con số của `SeedReport`, cùng việc `--demo` sẽ làm ở kế hoạch giai đoạn 4 (cần logic đặt vé).
