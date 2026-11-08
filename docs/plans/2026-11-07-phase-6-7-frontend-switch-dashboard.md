# Giai đoạn 6 & 7: Chuyển giao diện React sang FastAPI + Dashboard dữ liệu thật — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- **Giai đoạn 6:** giao diện React lấy toàn bộ dữ liệu sự kiện qua API FastAPI/PostgreSQL. `npm run dev` chạy uvicorn thay cho Node. Xoá `server/` và các file dữ liệu sự kiện tĩnh.
- **Giai đoạn 7:** dashboard Ban tổ chức chạy bằng số liệu thật: tab Doanh thu/Số vé, ngăn kéo sự kiện, lọc Tất cả · Đang bán · Sắp mở bán · Chờ duyệt · Đã diễn, ô "Mở bán lúc".

**Architecture:**
- **Frontend:**
  - Hook dữ liệu: `useHome`, `useEvent`, `useEvents`, `useMap`, `useCoupon`, `useOrganizerData`, `useEventDetail`.
  - Hàm thuần chuyển thẻ API sang props cũ của từng card: `src/lib/cards.js`.
  - Hàm thuần dựng lại object sự kiện kiểu cũ (`Date`…) từ JSON API: `reviveEvent` trong `src/lib/eventFormat.js`. File này chứa các hàm định dạng đang có ở `src/lib/events.js`, phần ghép dữ liệu thì bỏ đi.
- **Backend (giai đoạn 7):**
  - `phase`, `saleOpensAt`, `reviewedAt` trong `eventSummary`.
  - `saleStart` khi tạo sự kiện.
  - `GET /api/organizer/stats?days=7`, `GET /api/organizer/events/{id}`.
- **Test:**
  - Backend dùng pytest như cũ.
  - Frontend thêm **Vitest + Testing Library + jsdom**. Fixture JSON được chụp từ **API thật** (`src/test/fixtures/*.json`, sinh bằng script) nên test giao diện bám đúng hợp đồng dữ liệu.

**Tech Stack:** React 19, Vite 8, Vitest, @testing-library/react, jsdom; FastAPI, SQLAlchemy, PostgreSQL 18.

**Spec:**
- `docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 6 hook phía React, mục 7 dòng giai đoạn 6).
- `docs/superpowers/specs/2026-11-06-organizer-dashboard-live-data-design.md` (giai đoạn 7, điều chỉnh: dữ liệu ở bảng `events` thay cho `org_events`, SQL qua SQLAlchemy).

## Global Constraints

- **Không tạo git commit.** Thứ duy nhất được xoá là những gì spec đã duyệt cho xoá (`server/`, dữ liệu sự kiện tĩnh). Mọi file đó vẫn còn trong commit `1735fb3`, nên khôi phục được.
- Đường dẫn NFD, scratchpad, `MSYS_NO_PATHCONV=1`: như các giai đoạn trước.
- Test backend: `cd backend && .venv/Scripts/python.exe -m pytest -p no:cacheprovider`. Test frontend: `npm test` (`vitest run`).
- **Giao diện phải giữ nguyên.** Card và section giữ nguyên markup, chỉ đổi nguồn dữ liệu. Các thay đổi đã được người dùng chấp nhận gồm: thẻ hiển thị dữ liệu thật (ngày/giờ/giá theo DB), gộp sự kiện "Đêm 4", và nhãn "SẮP MỞ BÁN" lấy theo `status`.
- Link sang trang sự kiện dùng **slug từ API**, không dùng `slugify(title)` nữa, vì sự kiện của Ban tổ chức có thể có hậu tố `-2`.
- Lỗi API hiển thị bằng `err.message` (đã là câu tiếng Việt). Khi đang tải thì hiện khung chờ hoặc "Đang tải…" như các trang đang làm.
- Proxy Vite: `/api` → `http://localhost:8000`.
- Giai đoạn 7: `FEE_RATE = 5`. Doanh thu = `orders.total` của đơn `paid` (Ban tổ chức chịu giảm giá). Phí và thực nhận tính trên doanh thu đó.

## Review Focus

1. **Trang sự kiện, trang đặt vé, sơ đồ ghế/khu với sự kiện của Ban tổ chức** (slug có hậu tố, không có `map`, không nằm trong danh mục cũ): phải hiện và đặt được. Test thuộc Task 4, 5.
2. **Mã giảm giá ở bước thanh toán**: mã viết thường, mã sai, đơn dưới mức tối thiểu đều phải báo đúng như trước, dù giờ kiểm tra qua API. Test thuộc Task 5.
3. **Dashboard khi chưa có đơn hoặc chưa có sự kiện**: biểu đồ hiện trạng thái trống, không ra NaN. Ngăn kéo và bộ lọc không lỗi khi danh sách rỗng. Test thuộc Task 9, 10.
4. **Giờ mở bán**: sự kiện có `saleStart` ở tương lai thì phía khách hiện đếm ngược "Sắp mở bán" và server từ chối đặt vé. Dashboard xếp sự kiện đó vào tab "Sắp mở bán". `saleStart` sau giờ diễn thì 400. Test thuộc Task 8, 10.
5. **Ban tổ chức xem chi tiết sự kiện của người khác** (`/organizer/events/{id}`): phải 404. Số liệu ngăn kéo phải khớp: tổng tiền các hạng vé − giảm giá = doanh thu. Test thuộc Task 8.

---

## GIAI ĐOẠN 6

### Task 1: Hạ tầng test frontend + fixture từ API thật + tách `eventFormat`

**Files:**
- Create: `vitest.config.js` (hoặc mục `test` trong `vite.config.js`), `src/test/setup.js`, `scripts/capture-fixtures.mjs`, `src/test/fixtures/*.json`, `src/lib/eventFormat.js`, `src/lib/eventFormat.test.js`
- Modify: `package.json` (devDeps `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`; script `"test": "vitest run"`)

**Interfaces — Produces:**
- `eventFormat.js` (chuyển từ `events.js`, giữ nguyên chữ ký):
  - `slugify`, `eventPath(title)`, **`slugPath(slug)`**, `bookingPath(slug, showId)`
  - `formatEventDate`, `formatShortDate`, `formatShow`, `priceGroups`, `LAYOUT_LABEL`, `showIdOf`
- **`reviveEvent(api) -> event`**: đổi `start`, `shows[].start`, `saleOpensAt` sang `Date`, giữ nguyên các trường khác. `related` được chuyển qua `toTicketCard`.
- `capture-fixtures.mjs`: gọi API đang chạy ở `:8000` rồi ghi các file `home.json`, `event-list.json`, `event-zones.json`, `event-seats.json`, `map-<zones>.json`, `map-<seats>.json`, `availability-seats.json`, `categories.json`, `coupon-NHIP50.json`, `org-me.json` (tạo tạm một Ban tổ chức thử để chụp, rồi dọn).

- [ ] **Step 1:** Cài devDeps, viết `setup.js` (jest-dom), chạy `npm test`. Kết quả mong đợi: "No test files found" (hạ tầng đã chạy được).
- [ ] **Step 2: Test thất bại** `eventFormat.test.js`

```js
test('reviveEvent turns ISO strings into Dates in Vietnam time', () => {
  const ev = reviveEvent(fixture('event-zones'))
  expect(ev.start).toBeInstanceOf(Date)
  expect(ev.shows[0].start.getTime()).toBe(Date.parse(fixture('event-zones').shows[0].start))
  expect(ev.saleOpensAt === null || ev.saleOpensAt instanceof Date).toBe(true)
})
test('slugPath uses API slug as-is', () => expect(slugPath('dem-nhac-2')).toBe('/su-kien/dem-nhac-2'))
test('formatShow keeps legacy output', () => expect(formatShow({ startTime: '19:00', endTime: '23:00', start: new Date('2026-11-15T19:00:00+07:00') })).toBe('19:00 – 23:00, Chủ nhật, 15 tháng 11, 2026'))
test('priceGroups groups zones by group', ...)   // dùng tiers của event-zones fixture
```
- [ ] **Step 3: FAIL** → **Step 4: cài đặt** (chuyển hàm thuần sang file mới. `events.js` tạm thời re-export, để các file chưa chuyển vẫn chạy) → **Step 5: PASS**, `npm run build` vẫn thành công → ghi ledger.

### Task 2: Lớp chuyển thẻ API sang props cũ (`src/lib/cards.js`)

**Interfaces — Produces** (đầu vào là `EventCard`/`HomeCard` của API, đầu ra là đúng props mà card cũ đang đọc, kèm `slug`):
- `toTicketCard(c)` → `{id, slug, title, city, date: 'dd Th m', price: minPrice/1000, category}`
- `toEventCard(c, section)` → `{id, slug, status: 'SẮP MỞ BÁN' | 'MỚI MỞ BÁN', date: 'dd.mm.yyyy', time, title, venue: 'venue, city'}`
- `toTrendingCard(c)` → `{id, slug, rank, num, date: 'dd.mm', title}`
- `toPosterCard(c)` → `{id, slug, title, tag, date: 'dd.mm', tilt}`
- `toResaleCard(c)` → `{id, slug, title, meta: 'city · dd Th m', count: resaleCount, line}`
- `toHeroBanner(c)` → `{id, slug, no, status: 'SẮP MỞ BÁN' | 'ĐANG MỞ BÁN', title, venue: 'venue · city', weekday: 'CHỦ NHẬT', day: 'dd', month: 'TH mm', time}`
- `toScheduleItem(c, kind: 'weekend' | 'month')` → `{id, slug, day: 'T7' | 'CN' | 'dd.mm', time, title, venue, price: minPrice/1000}`
- `toCatalogCard(c)` → `{id, slug, title, city, cityId: meta.cityId, date: 'dd Th m', price: minPrice/1000, category}`

- [ ] **Step 1: Test thất bại** `cards.test.js`: với mỗi hàm, lấy thẻ đầu tiên của khu tương ứng trong `home.json` và kiểm tra **đúng định dạng chuỗi của card cũ**. Ví dụ hero của sự kiện Tinh Hà phải ra `{day: '15', month: 'TH 11', weekday: 'CHỦ NHẬT', time: '19:00'}`, và `toTicketCard` cho giá 800k ra `price === 800`.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS** → ghi ledger.

### Task 3: Trang chủ đọc từ `/api/home` (hook `useHome`) + card dùng slug

**Files:**
- Create: `src/hooks/useHome.js`, `src/components/sections/HomeSections.test.jsx`
- Modify: `HeroBanner`, `FeaturedEvents`, `TrendingEvents`, `PosterBoard`, `ResaleMarket`, `WeekendSchedule`, `CategoryRow`, `CityExplorer` (sections); `EventCard`, `PosterCard`, `ResaleCard`, `SquareEventCard`, `TicketCard`, `TrendingCard` (link `slug ? slugPath(slug) : eventPath(title)`).

**Interfaces — Produces:**
- `useHome() -> {sections, loading, error}`. Gọi `/api/home` **một lần cho mỗi lần tải trang**, giữ kết quả trong một promise cấp module (`resetHomeCache()` dùng cho test).
- Mỗi section nhận dữ liệu từ `useHome` qua lớp chuyển đổi của Task 2. Khi đang tải thì hiện khung xám như placeholder đang dùng.

- [ ] **Step 1: Test thất bại**: mock `api` trả `home.json`, render `<MemoryRouter><HeroBanner/></MemoryRouter>`. Kiểm tra:
  - có tiêu đề sự kiện hero đầu tiên, và link trỏ tới `/su-kien/<slug>`;
  - FeaturedEvents ở tab "Sắp mở bán" render đủ 4 thẻ của `featured-upcoming`;
  - CityExplorer lọc theo `meta.cityId`;
  - WeekendSchedule có 4 dòng;
  - khi api lỗi thì không văng exception và hiện thông báo.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS**, `npm run build` → ghi ledger.

### Task 4: Trang sự kiện + tìm kiếm + Sự kiện cộng đồng đọc từ API

**Files:** Modify `src/hooks/useEvent.js` (`useEvent(slug)` → `/api/events/{slug}` + `reviveEvent`; `useCommunityEvents` → `/api/events?organizer=1&sort=reviewed&limit=12`; thêm `useEvents(params)`), `src/pages/EventPage.jsx` (bỏ `getEvent`, `relatedEvents`, dùng `event.related`), `FilterResults.jsx` (`useEvents({q} | {category})`), `CommunityEvents.jsx`. Create `src/hooks/useEvent.test.jsx`, `src/pages/EventPage.test.jsx`.

- [ ] **Step 1: Test thất bại**:
  - `useEvent` trả `loading` rồi ra event đã có `Date`; slug không có thì ra `event === null` và trang hiện NotFound.
  - EventPage với fixture `event-zones` render tên, bảng giá theo nhóm và 4 thẻ liên quan.
  - FilterResults với `q` gọi `/api/events?q=…` (kiểm tra URL) rồi render kết quả.
  - Sự kiện của Ban tổ chức (fixture lấy từ `org-me` + chi tiết) render được dù không có `map`.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS**, build → ghi ledger.

### Task 5: Đặt vé: sơ đồ + mã giảm giá qua API

**Files:**
- Create: `src/hooks/useMap.js` (`/api/maps/{id}`, cache theo id), `src/hooks/useCoupon.js` (`check(code) -> {code, amount, minOrder} | throws`), `src/pages/BookingPage.test.jsx`
- Modify: `TicketPickers.jsx` (nhận `map` qua props thay vì `ZONE_MAPS` / `getSeatMap`), `BookingPage.jsx` (`useMap(event.map)`, `seatById` từ `map.seats`, coupon qua `useCoupon`, giữ `HOLD_MINUTES`/`MAX_PER_ORDER` trong `rules.js`), `PaymentStep.jsx` (nhận `coupon` object), `src/data/rules.js` (bỏ `COUPONS`)

- [ ] **Step 1: Test thất bại**, render BookingPage với các fixture:
  - Sự kiện bán theo ghế: sơ đồ hiện đủ số ghế của `map-seats`, ghế trong `availability-seats.unavailableSeats` bị vô hiệu.
  - Sự kiện bán theo khu: hiện đủ khu.
  - Nhập `nhip50` thì gọi `/api/coupons/nhip50` và hiện "✓ Đã áp dụng NHIP50" khi đủ tiền. Đơn nhỏ thì hiện "Mã NHIP50 cần đơn từ 500.000 ₫". Mã sai thì hiện câu lỗi từ API.
  - Bấm đặt vé thì POST `/api/orders` với đúng body cũ.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS**, build → ghi ledger.

### Task 6: Chuyển máy chủ: FastAPI thay Node + phục vụ `dist/` khi chạy thật + dọn dữ liệu tĩnh

**Files:**
- Create: `scripts/dev-api.mjs` (spawn `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`, đường dẫn tuyệt đối, có dấu cách), `backend/tests/test_spa.py`
- Modify:
  - `package.json`:
    - `dev:api` → `node scripts/dev-api.mjs`
    - `start` → uvicorn với `ENV=prod`
    - bỏ dependency `express`
    - `dev` giữ `concurrently`
  - `vite.config.js`: proxy sang `:8000`.
  - `backend/app/main.py`: khi `ENV=prod` và có `../dist`, mount static, và mọi đường dẫn không phải `/api` trả về `index.html`.
  - `README.md` gốc.
- Move: `src/data/eventDetails.js`, `src/data/venueMaps.js`, `src/lib/seating.js`, phần ghép dữ liệu của `src/lib/events.js`, cùng các trường dữ liệu sự kiện trong `home.js`/`hero.js`/`discover.js` sang `backend/seed/legacy/`. Sửa import trong `export_catalog.mjs`, `dump_legacy_*.mjs`, để vẫn tái tạo được `catalog.json` và fixture.
- Delete: `server/`, `src/lib/events.js` (sau khi mọi import đã trỏ sang `eventFormat.js`).

- [ ] **Step 1: Test thất bại** `test_spa.py`: với `ENV=prod` và một thư mục `dist` tạm có `index.html`:
  - `/su-kien/abc` trả `index.html` (200, text/html);
  - `/api/khong-co` vẫn trả JSON 404;
  - `/assets/x.js` trả file tĩnh.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt + dọn file.**
  - `grep -r "@/lib/events'\|data/eventDetails\|data/venueMaps\|lib/seating" src` phải không còn kết quả.
  - Chạy lại `TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs` thì `catalog.json` **không đổi** (bỏ qua `generatedAt`).
- [ ] **Step 4: PASS**: pytest, `npm test`, `npm run build` đều xanh.
- [ ] **Step 5: Chạy thật.** `npm run dev` lên `:5173`, dùng FastAPI. Dùng curl qua proxy kiểm tra `/api/home`, `/api/auth/me`. Mở trang bằng trình duyệt hoặc chụp màn hình nếu có công cụ. Đi hết luồng đăng ký → xem sự kiện → đặt vé (theo khu, theo ghế, loại vé) → vé của tôi. Ghi ledger.

---

## GIAI ĐOẠN 7

### Task 7: (dự phòng) Sửa lỗi phát sinh khi chạy thật ở Task 6

Lỗi nào phát hiện trong lúc chạy thật đều phải có test RED trước khi sửa. Không có lỗi thì bỏ qua task này và ghi vào ledger.

### Task 8: Backend dashboard: `saleStart`, `phase`, `/organizer/stats`, `/organizer/events/{id}`

**Files:** Modify `backend/app/services/manage.py`, `backend/app/routers/manage.py`. Create `backend/tests/test_api_dashboard.py`.

**Interfaces — Produces:**
- `OrgEventIn.saleStart` (`"YYYY-MM-DDTHH:mm"`, giờ VN, không bắt buộc):
  - sai định dạng → 400 `Giờ mở bán không hợp lệ`;
  - không trước giờ diễn → 400 `Giờ mở bán phải trước giờ diễn`;
  - lưu vào `events.sale_start`.
- `eventSummary` thêm `phase`, `saleOpensAt` (ISO), `reviewedAt` (ISO). `phase` gồm:
  - `pending`, `rejected` (theo trạng thái duyệt);
  - `ended`: đã duyệt, và ngày diễn (VN) của suất cuối nhỏ hơn hôm nay;
  - `upcoming-sale`: đã duyệt, `saleOpensAt > now`, với `saleOpensAt = sale_start` hoặc `reviewed_at`;
  - `on-sale`: còn lại.
- `GET /organizer/stats?days=` (1–31, mặc định 7) → `{days:[{date, label: 'T2'…'CN', revenue, tickets}]}`. Đủ N ngày kết thúc ở hôm nay (VN), từ cũ đến mới. Chỉ tính đơn `paid` thuộc sự kiện của Ban tổ chức này.
- `GET /organizer/events/{id}` → `{tiers:[{id,name,price,capacity,sold,revenue}], timeline:{createdAt,reviewedAt,saleOpensAt,startsAt}, money:{gross,discount,revenue,fee,net,orders}, recentOrders:[5]}`.
  - Sự kiện không thuộc mình thì 404 `Sự kiện không tồn tại`.
  - `gross` = Σ`price × qty`, `revenue` = Σ`total` = `gross − discount`, `fee` = `round(revenue × 5%)`, `net` = `revenue − fee`.

- [ ] **Step 1: Test thất bại**:
  - `saleStart` hợp lệ được lưu. Sai định dạng hoặc sau giờ diễn thì 400.
  - Sự kiện đã duyệt có `saleStart` ở tương lai thì `phase` là `upcoming-sale`, `/api/events/{slug}` có `status` là `coming`, và POST `/orders` bị 400 "Sự kiện chưa mở bán".
  - Suất đã qua thì `ended`.
  - `stats`: 7 ngày, ngày không có đơn là 0. Đơn lúc 23:30 VN tính vào đúng ngày VN. Đơn có giảm giá thì tính `total`. Đơn của Ban tổ chức khác không bị tính. `days=0` thì 400.
  - Chi tiết sự kiện: số liệu đúng, `gross − discount == revenue`, sự kiện của người khác thì 404, khách thường thì 403.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

### Task 9: Hook và hàm thuần cho dashboard

**Files:** Create `src/hooks/useOrganizerData.js`, `src/hooks/useEventDetail.js`, `src/lib/dashboard.js`, `src/lib/dashboard.test.js`, `src/hooks/useOrganizerData.test.jsx`.

**Interfaces — Produces:**
- `dashboard.FILTERS = [{id:'tat-ca'…'Tất cả'}, {id:'dang-ban','Đang bán'}, {id:'sap-mo-ban','Sắp mở bán'}, {id:'cho-duyet','Chờ duyệt'}, {id:'da-dien','Đã diễn'}]`
- `dashboard.filterEvents(events, loc) -> events`. Tab `cho-duyet` gồm cả `pending` lẫn `rejected`. `loc` không hợp lệ thì coi như `tat-ca`.
- `dashboard.countByFilter(events) -> {loc: n}`
- `dashboard.STATUS` (theo `phase`, thêm `upcoming-sale` với nhãn "Sắp mở bán")
- `dashboard.stamp(ev) -> label`. Nhãn của `upcoming-sale` có dạng "Sắp mở bán · dd/MM HH:mm".
- `useOrganizerData() -> {data, stats, error, reload}`: gọi `/organizer/me` và `/organizer/stats` song song, tự làm mới mỗi 15 giây, dọn interval khi unmount.
- `useEventDetail(id) -> {detail, loading, error}`: chỉ gọi khi `id` khác null, giữ cache theo id, có `reload`.

- [ ] **Step 1: Test thất bại**: lọc và đếm với danh sách đủ 5 phase, danh sách rỗng, và `loc` lạ. Hook gọi hai API song song. Dùng fake timer để kiểm tra 15 giây sau gọi lại, và unmount thì dừng.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS** → ghi ledger.

### Task 10: Giao diện dashboard Ban tổ chức (`OrganizerDashboard.jsx`, `widgets.jsx`)

**Thay đổi:**
- **Biểu đồ:** dùng `stats.days` thay `sample.week`, bỏ nhãn "DỮ LIỆU MẪU". `BarChart` dùng `key` là `date`, chặn `max = 0` và hiện câu "Chưa có đơn trong 7 ngày qua".
- **Thanh lọc:** đặt trên ngăn kéo, có số đếm mỗi tab, đọc và ghi `?loc=` qua `useSearchParams`.
- **Ngăn kéo (accordion):** mỗi lúc mở một sự kiện, có `aria-expanded`. Nội dung gồm:
  - Mốc thời gian: Gửi → Duyệt → Mở bán → Diễn, kèm đếm ngược tới mốc kế tiếp.
  - Theo loại vé: thanh `Progress`.
  - Dòng "Giảm giá −X".
  - Doanh thu / phí 5% / thực nhận / số đơn.
  - 5 đơn gần đây.
  - Nút "Mở trang sự kiện" và "Sao chép link" (chỉ khi đã duyệt).
  - Sự kiện bị trả lại thì hiện lý do.
- **Con dấu và thẻ thống kê:** theo `phase`.
- **Form tạo sự kiện:** thêm ô "Mở bán lúc" (`datetime-local`), gửi `saleStart` (bỏ trống thì không gửi).
- **Dọn dẹp:** xoá `organizer.week` trong `src/data/dashboards.js`. Đổi chữ "Sắp diễn" còn sót thành "Sắp mở bán".

**Files:** Modify `src/pages/OrganizerDashboard.jsx`, `src/components/dashboard/widgets.jsx`, `src/data/dashboards.js`. Create `src/pages/OrganizerDashboard.test.jsx`.

- [ ] **Step 1: Test thất bại** (mock api với `org-me.json` cộng `stats` và `detail` dựng trong test):
  - Bấm tab "Số vé" thì cột biểu đồ đổi giá trị.
  - Stats toàn 0 thì hiện câu trạng thái trống, không có `NaN` trong DOM.
  - Bấm tab "Sắp mở bán" thì chỉ còn sự kiện `upcoming-sale`, và URL có `?loc=sap-mo-ban`.
  - Bấm một sự kiện thì ngăn kéo mở (`aria-expanded=true`) và gọi `/organizer/events/{id}`. Hiện đúng "Giảm giá −…" và "Thực nhận". Bấm lại thì đóng.
  - Form tạo sự kiện gửi `saleStart`.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS**, `npm run build` → ghi ledger.

### Task 11: Kết thúc

- [ ] Chạy `python -m app.seed --demo` trên DB dev. Chạy thật `npm run dev`, đăng nhập một Ban tổ chức có sự kiện đã duyệt và có đơn, xem biểu đồ, lọc và ngăn kéo.
- [ ] Postman: thêm "Thống kê 7 ngày" và "Chi tiết sự kiện (ngăn kéo)".
- [ ] README gốc: cách chạy mới (`npm run dev` = FastAPI + Vite, `npm test`, pytest).
- [ ] pytest, `npm test`, `npm run build` đều xanh. Gọi reviewer mới review toàn bộ giai đoạn 6 và 7.
