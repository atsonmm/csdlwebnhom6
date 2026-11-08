# Chuyển server TicketNhịp sang FastAPI + PostgreSQL

Ngày: 2026-11-06 · Dự án: `ticketnhip/` · Hạn: khoảng 2 tháng (bảo vệ cuối kỳ môn **CSDL Web**)

## 1. Mục đích

Học phần CSDL Web bắt buộc dùng **Python/FastAPI** làm server cung cấp API cho React, **PostgreSQL** làm CSDL (quản lý bằng **pgAdmin4**) và thử API bằng **Postman**. Server hiện tại là Node.js/Express + SQLite nên không đạt yêu cầu này. Ngoài ra, phần lớn danh mục sự kiện đang nằm trong file JS chứ không ở trong CSDL.

Mục tiêu: web vẫn chạy **y như hiện tại** trên giao diện người dùng, nhưng mọi dữ liệu nằm trong PostgreSQL và mọi API do FastAPI phục vụ. Sau đó làm tiếp dashboard dữ liệu thật trên nền mới (thiết kế riêng: `2026-11-06-organizer-dashboard-live-data-design.md`).

Người làm chính: người dùng (với Claude hỗ trợ). Cả nhóm 4 người không chia việc phần này.

## 2. Mục tiêu / Không làm / Điều cấm

**Mục tiêu**
- Toàn bộ danh mục sự kiện nằm trong PostgreSQL: sự kiện, loại vé, suất diễn, sơ đồ khu/ghế, danh mục, mã giảm giá, vị trí sự kiện trên trang chủ. Cùng với đó là người dùng, phiên đăng nhập, Ban tổ chức, đơn hàng, vé.
- 16 API hiện có được viết lại bằng FastAPI, giữ **nguyên đường dẫn và dạng JSON** để giao diện thay đổi ít nhất có thể. Bổ sung các API đọc danh mục mà giao diện cần.
- React đọc sự kiện qua API, không `import` dữ liệu sự kiện từ `src/data` hay `src/lib/events.js` nữa.
- Lược đồ chuẩn hoá, có khoá ngoại, CHECK, UNIQUE. Vẽ được ERD trong pgAdmin4. Có file `schema.sql` xuất ra để đưa vào báo cáo.
- Mỗi giai đoạn có bộ request Postman (collection) và test pytest.

**Không làm**
- Không đổi giao diện hay trải nghiệm người dùng (trừ chỗ bắt buộc vì đổi nguồn dữ liệu, như trạng thái đang tải).
- Không chuyển dữ liệu từ SQLite cũ sang. Đó chỉ là dữ liệu thử lúc phát triển, DB mới được nạp lại từ đầu.
- Không đưa nội dung trang trí vào DB: ảnh và màu banner, blog, thành phố, gói thành viên, đối tác coupon, chính sách, menu, ngôn ngữ, từ khoá gợi ý. Các phần này vẫn ở `src/data/` *(quyết định của Claude, xem mục 8)*.
- Không cập nhật các gói `ban-giao/`.

**Điều cấm**
- Hai server cùng ghi dữ liệu thật vào hai CSDL khác nhau trong lúc giao diện đang dùng cả hai.
- Giữ lại logic "mô phỏng bằng hàm băm" ở server mới. Số vé đã bán sẵn phải là dữ liệu trong bảng.
- Để một sự kiện tồn tại ở hai nơi (file JS và DB) sau khi đã chuyển giao diện.
- Bán trùng ghế hoặc bán vượt sức chứa khi hai người đặt cùng lúc.

## 3. Cách làm đã cân nhắc

**Công nghệ** (người dùng chọn): FastAPI + **SQLAlchemy 2.0 (ORM)** + Alembic + driver `psycopg` 3 + PostgreSQL 18. Phương án SQL viết tay bằng psycopg bị bỏ vì người dùng chọn ORM, phù hợp với hướng dẫn của học phần.

**Danh mục sự kiện** (người dùng chọn): **đưa toàn bộ vào DB**, React đọc qua API. Hai phương án bị bỏ: (B) DB có nhưng giao diện vẫn đọc file JS, sinh hai nguồn dữ liệu; (C) Python đọc file JSON, danh mục không nằm trong CSDL.

**Cách chuyển** (người dùng chọn A):

| Cách | Mô tả | Đánh đổi |
|---|---|---|
| **A. Dựng song song ở `backend/`, chuyển theo giai đoạn** ✅ | Node cũ chạy tiếp để demo. FastAPI được dựng và kiểm thử từng giai đoạn bằng Postman/pytest. Khi đủ tính năng thì chuyển giao diện một lần và xoá `server/`. | Lúc nào cũng có bản chạy được. Có thời gian hai server cùng tồn tại. |
| B. Chia API theo đường dẫn giữa hai server | Vite chuyển một phần API sang FastAPI. | Hai CSDL khác nhau, dữ liệu dễ lệch. Bị loại. |
| C. Viết lại một lần | Xong hết mới chạy thử. | Nhiều tuần không chạy được gì. Rủi ro cao. |

## 4. Lược đồ PostgreSQL

Thời gian dùng `timestamptz`. Tiền dùng `integer` (VND, không có số lẻ). Mỗi bảng có chú thích (`COMMENT ON`) bằng tiếng Việt để ERD trong pgAdmin dễ đọc.

**Danh mục & địa điểm**
- `categories(id text PK, label, dot, sort_order)`: nạp từ `navigation.js: categories`.
- `venue_maps(id text PK, kind CHECK in ('zones','seats'), name, view_box, decor jsonb)`
- `map_groups(map_id FK, id, label, color, ink bool, max_per_order int CHECK > 0, perks)`, PK `(map_id, id)`: nhóm khu hoặc hạng ghế.
- `map_zones(map_id FK, id, label, group_id, capacity int CHECK > 0, shape jsonb, text jsonb)`, PK `(map_id, id)`, FK `(map_id, group_id)` → `map_groups`.
- `map_seats(map_id FK, id, row_label, num, group_id, x, y)`, PK `(map_id, id)`, FK tới nhóm. Ghế đã được sinh sẵn từ `getSeatMap`.

**Sự kiện** (gộp sự kiện có sẵn và sự kiện của Ban tổ chức vào **một** bảng)
- `events(id serial PK, slug UNIQUE, title, category_id FK, city, venue, address, layout CHECK in ('list','zones','seats'), map_id FK NULL, organizer_id FK → organizers NULL, host_name, host_bio, description text[], notes text[], status CHECK in ('pending','approved','rejected'), reject_reason, sale_start timestamptz NULL, resale_count int DEFAULT 0, created_at, reviewed_at)`
  - Sự kiện có sẵn: `organizer_id = NULL`, `status = 'approved'`, ban tổ chức hiển thị lấy từ `host_name/host_bio`.
  - CHECK: `layout = 'list'` thì `map_id IS NULL`, ngược lại thì `map_id IS NOT NULL`.
  - Sự kiện "SẮP MỞ BÁN" ở dữ liệu cũ (`status: 'coming'`, `saleOpensAt`): nạp vào `sale_start`. Cột này cũng phục vụ dashboard sau này.
- `shows(event_id FK, id text, starts_at timestamptz, end_time time)`, PK `(event_id, id)`. `id` giữ định dạng cũ `YYYYMMDD-HHMM` để đường dẫn `?suat=` không đổi.
- `ticket_tiers(event_id FK, id text, name, price int CHECK >= 0, capacity int CHECK >= 0, max_per_order int, perks, group_id NULL, sort_order)`, PK `(event_id, id)`. Sự kiện theo khu/ghế: mỗi khu hoặc hạng ghế là một dòng, như `finalize()` đang làm.
- `home_slots(section text, position int, event_id FK, meta jsonb)`, PK `(section, position)`: sự kiện nào xuất hiện ở khu nào của trang chủ (hero, featured-upcoming, featured-new, trending, posters, resale, schedule-weekend, schedule-month, catalog).
  - **Người dùng chọn: thẻ hiển thị dữ liệu thật.** Ngày, giờ, địa điểm, thành phố, giá ("từ …" = giá vé thấp nhất) và trạng thái bán đều lấy từ `events`/`shows`/`ticket_tiers` qua JOIN, không chép vào `meta`.
  - `meta` **chỉ** chứa phần thuần trang trí: `tilt`, `num`, `line`, `no`, `tag`, màu, ảnh, `cityId`… Đây không phải dữ liệu sự kiện.
  - Thẻ nào trùng sự kiện nhưng khác tên thì trỏ về **một** sự kiện. Ví dụ "Concert Đêm 4: Tinh Hà" trỏ về "Concert Đêm 4: Hẹn Giữa Tinh Hà". `export_catalog.mjs` có một bảng ánh xạ tên cũ → slug chuẩn, và in ra danh sách các thẻ bị đổi ngày, giá hoặc gộp để người dùng xem lại.
  - Hệ quả được chấp nhận: một số thẻ trên trang chủ đổi ngày hoặc giá so với bây giờ, để khớp với trang chi tiết. Kiểm tra ở giai đoạn 6 so sánh **thẻ với trang chi tiết**, không so với chữ cũ của thẻ.

**Kho vé**
- `tier_stock(event_id, show_id, tier_id, presold int CHECK >= 0, sold int CHECK >= 0, CHECK (presold + sold <= capacity của hạng))`, PK `(event_id, show_id, tier_id)`. Ràng buộc vượt sức chứa được kiểm tra trong transaction. CHECK chỉ kiểm được trong một dòng, nên `capacity` được chép sang cột `capacity` của bảng này.
- `seat_holds(event_id, show_id, seat_id, order_id FK NULL)`, PK `(event_id, show_id, seat_id)`. `order_id = NULL` nghĩa là ghế đã bán sẵn. PK chặn bán trùng.
- `presold` và `seat_holds` (đã bán sẵn) được tính **một lần lúc nạp dữ liệu** bằng đúng hàm băm cũ, nên số liệu khớp với web hiện tại.

**Người dùng & phiên**
- `users(id serial PK, name, email UNIQUE NULL, phone UNIQUE NULL, password_hash, role CHECK in ('customer','organizer','admin'), created_at, CHECK (email IS NOT NULL OR phone IS NOT NULL))`
- `sessions(token_hash PK, user_id FK CASCADE, expires_at timestamptz)`
- `password_resets(token_hash PK, user_id FK CASCADE, expires_at, used bool)`
- `organizers(user_id PK FK CASCADE, org_name, phone, description, created_at)`

**Bán vé**
- `coupons(code PK, amount int CHECK > 0, min_order int CHECK >= 0, active bool)`: nạp `NHIP50`.
- `orders(id text PK, user_id FK, event_id FK, show_id, subtotal, discount, coupon_code FK NULL, total, method CHECK in ('qr','wallet','card'), buyer_name, buyer_email, buyer_phone, status CHECK, created_at)`, FK `(event_id, show_id)` → `shows`. CHECK `total = subtotal - discount`. Bỏ các cột sao chép thông tin sự kiện (`event_title`, `venue`…), lấy qua JOIN.
- `order_items(order_id FK CASCADE, tier_id, price, qty CHECK > 0)`, PK `(order_id, tier_id)`, FK `(event_id, tier_id)` thông qua đơn. `price` là giá tại thời điểm mua (cố ý lưu lại).
- `tickets(code PK, order_id FK CASCADE, tier_id, price, seat_id NULL, checked_in_at NULL)`

**VIEW** (phục vụ báo cáo và dashboard): `v_event_sales(event_id, show_id, tier_id, sold, revenue)` và `v_daily_revenue(organizer_id, day, revenue, tickets)`, theo giờ Asia/Ho_Chi_Minh.

## 5. Nạp dữ liệu (seed)

Logic ghép danh mục hiện tại rất phức tạp (gộp nhiều nguồn, sinh giá trị mặc định bằng hàm băm). Vì vậy không viết lại nó bằng Python:
1. `backend/seed/export_catalog.mjs` (Node, chạy một lần): import `src/lib/events.js`, `venueMaps.js`, `seating.js`, `home.js`, `hero.js`, `discover.js`, xuất ra `backend/seed/catalog.json`. File gồm: categories, maps (đã sinh ghế), events (đã `finalize`, kèm shows và tiers), home_slots, presold theo từng show/hạng, danh sách ghế đã bán sẵn, coupons.
2. `catalog.json` được **commit kèm dự án**. Đây là nguồn nạp chính thức. Sau khi chuyển giao diện, có thể xoá các file JS dữ liệu sự kiện mà không mất gì.
3. `python -m app.seed` đọc `catalog.json` và ghi vào bảng theo kiểu **upsert theo khoá tự nhiên** (slug, show id, tier id, seat id). Chạy lại nhiều lần vẫn an toàn:
   - Giữ nguyên `events.id`, `tier_stock.sold`, `seat_holds` gắn với đơn, cùng người dùng và đơn hàng.
   - Chỉ làm mới các trường mô tả và `presold`.
   - Không đụng tới sự kiện của Ban tổ chức (`organizer_id IS NOT NULL`).
   - Có thêm `--reset`: xoá sạch toàn bộ dữ liệu rồi nạp lại từ đầu.

   Ngoài ra, lệnh này còn:    - tạo tài khoản admin (giống `seedAdmin` cũ);
   - với tuỳ chọn `--demo`: tạo thêm Ban tổ chức, sự kiện đủ các trạng thái, và đơn hàng rải đều trong 7 ngày (phục vụ dashboard và buổi bảo vệ). Chạy lại `--demo` chỉ thay thế dữ liệu do chính `--demo` tạo, không nhân đôi.
4. `export_catalog.mjs` chạy với `TZ=Asia/Ho_Chi_Minh`, vì ngày và mã suất diễn được tính theo giờ máy.

## 6. Server FastAPI

**Cấu trúc**
```
backend/
  app/
    main.py          # tạo app, gắn router dưới /api, xử lý lỗi → {"error": "..."}
    config.py        # pydantic-settings: DATABASE_URL, ADMIN_EMAIL/PASSWORD, ENV
    db.py            # engine, SessionLocal, get_db()
    models/          # class ORM theo nhóm: catalog.py, users.py, sales.py
    schemas/         # Pydantic: dữ liệu vào/ra
    routers/         # auth.py, events.py, orders.py, organizer.py, admin.py
    services/        # logic: booking.py (đặt vé), stock.py, auth.py (băm mật khẩu, phiên)
    seed.py
  alembic/           # migration
  seed/catalog.json, export_catalog.mjs
  tests/             # pytest + TestClient, DB riêng ticketnhip_test
  postman/ticketnhip.postman_collection.json
  requirements.txt  ·  .env.example  ·  README.md (cài đặt, tạo DB bằng pgAdmin)
```
- SQLAlchemy **đồng bộ** (không async): dễ đọc hơn, hiệu năng thừa cho bài này.
- Khi `ENV=dev` thì bật `echo` SQL ra log, để khi trình bày chỉ được câu SQL thật.

**API giữ nguyên** (đường dẫn + JSON như Node): `/auth/me`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/forgot`, `/auth/reset`, `/events/{slug}/availability`, `GET/POST /orders`, `GET /events`, `GET /events/{slug}`, `/organizer/register`, `/organizer/me`, `POST /organizer/events`, `/admin/overview`, `/admin/events/{id}/review`. Thông báo lỗi giữ nguyên tiếng Việt, dạng `{"error": "..."}`, cùng mã HTTP.

**API mới cho giao diện** (vì giao diện không còn import danh mục):
- `GET /events` (mở rộng): lọc `?q=&category=&city=&section=&limit=`. Trả về dạng thẻ (slug, title, city, venue, start, minPrice, category, status, saleOpensAt).
  - Lưu ý: hiện `/events` đang trả "sự kiện đã duyệt của Ban tổ chức" dạng `{slug, raw}`. Hai ý nghĩa này được gộp lại. Hook `useEvent.js` sửa theo.
- `GET /events/{slug}`: đầy đủ như object `finalize()` trả về hiện nay (shows, tiers, organizer, description, notes, layout, map id, related).
- `GET /maps/{id}`: sơ đồ khu/ghế (groups, zones hoặc seats, decor).
- `GET /home`: các khu trang chủ từ `home_slots`, mỗi khu là danh sách thẻ kèm `meta`.
- `GET /categories`, `GET /coupons/{code}` (kiểm tra mã ở bước thanh toán).

**Đăng nhập**: cookie httpOnly `tn_session`, giữ cơ chế cũ: token ngẫu nhiên, DB chỉ lưu sha256 của token, mật khẩu băm bằng `hashlib.scrypt` (n=16384, r=8, p=1, 64 byte, định dạng `scrypt$salt$hash`). Giới hạn đăng nhập sai giữ trong bộ nhớ như cũ. `require_user` / `require_role` viết thành dependency của FastAPI.

**Đặt vé** (`services/booking.py`, một transaction):
- Khoá dòng `tier_stock ... FOR UPDATE` (`with_for_update()`) theo thứ tự `tier_id` cố định để tránh deadlock, kiểm tra còn vé rồi cộng `sold`.
- Bán theo ghế: chèn `seat_holds`. Nếu trùng PK thì trả 409 "Ghế … vừa có người mua".
- Giữ nguyên các kiểm tra hiện có: chưa mở bán, suất diễn hợp lệ, tối đa 10 vé/đơn, `max_per_order` theo hạng, coupon, phương thức thanh toán, thông tin người nhận. Sinh mã đơn và mã vé theo bảng chữ cái cũ.

## 7. Giai đoạn

Mỗi giai đoạn chỉ xong khi: có migration Alembic, pytest chạy qua, có collection Postman, và có ghi chú README.

| # | Nội dung | Xong khi |
|---|---|---|
| 0 | Dựng `backend/`, venv, `requirements.txt`, tạo DB `ticketnhip` + `ticketnhip_test` bằng pgAdmin, kết nối được | `GET /api/health` trả về `{ok: true}` và đọc được phiên bản PostgreSQL |
| 1 | Lược đồ (models + migration) + `export_catalog.mjs` + `seed` | Số sự kiện, hạng vé, ghế trong DB khớp với `events.length` của bản JS. Xem được ERD trong pgAdmin |
| 2 | API danh mục: `/events`, `/events/{slug}`, `/maps/{id}`, `/home`, `/categories`, `/events/{slug}/availability` | JSON của `/events/{slug}` khớp với `getEvent(slug)` cũ (bỏ qua kiểu Date/chuỗi) trên mọi slug |
| 3 | Đăng nhập: register/login/logout/me/forgot/reset + phân quyền | Postman: đăng ký, đăng nhập, cookie, `/auth/me` |
| 4 | Đặt vé + `GET /orders` | Test đặt vé đồng thời không bán vượt hoặc trùng ghế |
| 5 | Ban tổ chức + Quản trị | Tạo sự kiện → duyệt → xuất hiện trong `/events` |
| 6 | **Chuyển giao diện**: sửa các component đang import dữ liệu sự kiện sang hook gọi API, Vite proxy `/api` → `:8000`, `npm run dev` chạy uvicorn thay cho Node, xoá `server/` và các file dữ liệu sự kiện không còn dùng | Đi hết các luồng: trang chủ → sự kiện → đặt vé (3 kiểu) → vé của tôi → BTC tạo sự kiện → admin duyệt. `npm run build` thành công |
| 7 | Dashboard dữ liệu thật (bản thiết kế riêng, điều chỉnh sang SQLAlchemy/VIEW) | Theo bản thiết kế đó |

## 8. Quyết định của Claude (người dùng có thể sửa)
- Nội dung trang trí vẫn ở `src/data/`. Chỉ những gì liên quan tới sự kiện và bán vé mới vào DB.
- Không chuyển dữ liệu SQLite cũ sang DB mới.
- Gộp `org_events` vào bảng `events` chung.
- Chuẩn hoá `orders`: bỏ các cột sao chép thông tin sự kiện.
- Tạo danh mục bằng cách xuất từ code JS hiện có (Node chạy một lần) thay cho viết lại logic ghép bằng Python.
- SQLAlchemy đồng bộ. pytest trên DB test riêng.
- FastAPI chạy cổng 8000. Thời gian lưu dạng `timestamptz`, hiển thị theo Asia/Ho_Chi_Minh.
- Trường `status` trong API giữ `coming`/`on-sale`. Là `coming` khi `sale_start` ở tương lai. Sự kiện của Ban tổ chức không đặt `sale_start` thì mở bán từ `reviewed_at`.
- Sự kiện kiểu `list`: `capacity` = `remaining` hiện tại, `presold` = 0 (đúng như hành vi hiện nay). Sự kiện bán theo ghế chỉ tính kho từ `seat_holds`. `tier_stock` chỉ dùng cho kiểu `list` và `zones`.
- `order_items` có thêm cột `event_id` để làm khoá ngoại ghép tới `ticket_tiers`.
- Tìm kiếm không dấu (`?q=`): dùng cột `search_text` đã chuẩn hoá, do Python điền. Không cần extension `unaccent`.
- `GET /events?organizer=1&sort=reviewed` cho khu "Sự kiện cộng đồng" (sự kiện Ban tổ chức đã duyệt, mới nhất trước).
- `/admin/overview.approvedEvents` chỉ đếm sự kiện có `organizer_id`, giống ý nghĩa cũ.
- Sự kiện do Ban tổ chức tạo giữ kiểu `list`, mã hạng `ve-N`.
- Khi chạy thật (production), FastAPI phục vụ luôn `dist/`, có fallback về `index.html` (thay cho `npm start`).
- Hook phía React chuyển chuỗi ISO về `Date`, để các component đang gọi `.getDate()` / `.getTime()` không phải sửa.

## 9. Ràng buộc môi trường
- Windows 11, Python 3.14, PostgreSQL 18 + pgAdmin 4 đã cài ở `C:\Program Files\PostgreSQL\18`. `psql` chưa có trong PATH: dùng đường dẫn đầy đủ hoặc pgAdmin.
- Mật khẩu tài khoản `postgres` do người dùng giữ. Ghi vào `backend/.env` (không commit, có `.env.example`).
- Thư mục dự án nằm dưới đường dẫn Unicode NFD ("Tài liệu"). Tạo file phải kiểm tra không sinh thư mục trùng.
- Dự án chưa có git. Nên `git init` ở giai đoạn 0 để theo dõi thay đổi.

## 10. Để lại cho người dựng
- Chia nhỏ module, đặt tên class/biến, nội dung README.
- Cách tổ chức hook phía React (`useEvents`, `useEvent`, `useHome`, `useMap`…) và trạng thái đang tải.
- Danh sách chính xác các component phải sửa ở giai đoạn 6 (tìm bằng grep `@/lib/events` và `@/data/{home,hero,discover,eventDetails,venueMaps}`).
