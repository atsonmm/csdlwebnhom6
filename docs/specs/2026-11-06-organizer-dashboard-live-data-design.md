# Dashboard Ban tổ chức — chạy bằng dữ liệu thật

Ngày: 2026-11-06 · Trang: `/ban-to-chuc` (`src/pages/OrganizerDashboard.jsx`)

## 1. Mục đích

Ba phần trên bàn làm việc của Ban tổ chức đang dùng dữ liệu mẫu hoặc còn thiếu. Người dùng muốn chúng **chạy bằng dữ liệu thật** từ DB:

1. Biểu đồ "Xấp vé bán ra · 7 ngày" với tab **Doanh thu / Số vé**.
2. **Ngăn kéo sự kiện**: bấm vào một sự kiện để xem chi tiết.
3. **Lọc trạng thái**: Tất cả · Đang bán · Sắp mở bán · Chờ duyệt · Đã diễn.

## 2. Mục tiêu / Không làm / Điều cấm

**Mục tiêu**
- Mọi con số trong ba phần trên đều lấy từ DB (`orders`, `order_items`, `org_events`). Bỏ nhãn "DỮ LIỆU MẪU" ở biểu đồ.
- Thêm khái niệm **giờ mở bán** cho sự kiện do Ban tổ chức tạo. Trạng thái "Sắp mở bán" có ý nghĩa thật ở cả dashboard lẫn phía khách.

**Không làm (lần này)**
- Sửa hoặc huỷ sự kiện, soát vé tại cổng, các mục menu "Hoá đơn", "Báo cáo".
- Không đổi dữ liệu mẫu ở trang Quản trị (`AdminDashboard`).
- Không đưa sự kiện "Sắp mở bán" của Ban tổ chức vào tab "Sắp mở bán" ở trang chủ.
- Không thêm thư viện mới.

**Điều cấm** (làm thế là hỏng, dù vẫn "chạy được")
- Vẽ số giả khi chưa có đơn. Không có đơn thì biểu đồ hiện trống, kèm một dòng giải thích.
- Chỉ ẩn nút mua ở giao diện mà server vẫn nhận đơn trước giờ mở bán.
- Khoá lại những sự kiện đang bán sẵn khi chạy migration.

## 3. Cách làm đã cân nhắc

| Cách | Mô tả | Đánh đổi |
|---|---|---|
| **A. State cục bộ + hook tự viết** ✅ *đã chọn* | `OrganizerDesk` giữ `mode`, `filter`, `openId`. Lọc trên client bằng `useMemo`. Hook `useOrganizerData`, `useEventDetail`. | Không thêm thư viện, theo đúng kiểu code đang có, nhóm dễ đọc. Phải tự lo cache, nhưng ở quy mô này đơn giản. |
| B. TanStack Query | Thư viện tự lo cache, làm mới định kỳ, tải lười. | Thêm thư viện và cách nghĩ mới cho cả nhóm, chỉ để phục vụ một trang. |
| C. Kho state chung (Context/Zustand) | Dữ liệu dashboard để ở kho toàn cục. | Chỉ một trang dùng, nên chỉ thêm phức tạp. |

**Định nghĩa "Sắp mở bán"**: người dùng chọn cách **theo giờ mở bán**, không theo ngày diễn hay theo số vé còn lại. Người dùng cũng chọn chữ **"Sắp mở bán"** thay cho "Sắp diễn".

## 4. Thiết kế

### 4.1 Dữ liệu & DB (`server/db.js`)
- Thêm cột `org_events.sale_start TEXT` (ISO có múi giờ). Migration theo kiểu đang dùng (`PRAGMA table_info` → `ALTER TABLE`).
- Dữ liệu cũ: `sale_start = NULL`, nghĩa là **mở bán từ lúc được duyệt** (`reviewed_at`). Sự kiện đang bán không bị khoá.

### 4.1b Cách tính doanh thu (người dùng chọn: **Ban tổ chức chịu mã giảm giá**)
- **Doanh thu = `orders.total`** (tiền khách thực trả, sau giảm giá). Mọi nơi đều dùng chung cách này: biểu đồ, thẻ "Tổng doanh thu", số dư rút về, `eventSummary.revenue` (đã đúng sẵn), ngăn kéo.
- **Phí sàn 5% tính trên doanh thu này**: thực nhận = `total × 95%`.
- Doanh thu theo loại vé lấy từ `order_items` (`price × qty`, chưa trừ giảm giá). Ngăn kéo hiện thêm dòng **"Giảm giá −X"** (X = `SUM(orders.discount)` của sự kiện) ngay dưới các loại vé, để: tổng các loại vé − giảm giá = doanh thu.

### 4.2 Trạng thái `phase` (server tính, không lưu)
Viết một hàm `phaseOf(row, now)` trong `server/manage.js`, dùng chung cho mọi nơi:

| phase | Điều kiện | Nhãn |
|---|---|---|
| `pending` | status = pending | Chờ duyệt |
| `rejected` | status = rejected | Bị trả lại |
| `ended` | approved, đã qua ngày diễn (quy tắc hiện tại: `date + 1 ngày < now`) | Đã diễn |
| `upcoming-sale` | approved, `now < saleOpensAt` | Sắp mở bán · dd/MM HH:mm |
| `on-sale` | approved, còn lại | Đang bán |

`saleOpensAt` bằng `sale_start`, nếu trống thì lấy `reviewed_at`. Nếu sàn duyệt **sau** giờ mở bán đã đặt thì sự kiện mở bán ngay khi được duyệt.

Tab lọc **"Chờ duyệt" gồm cả `pending` lẫn `rejected`**, vì Ban tổ chức cần xử lý cả hai.

### 4.3 Phía khách
- `rowToRaw` (`server/manage.js`): đặt `status: 'coming'` khi `now < saleOpensAt`, ngược lại là `'on-sale'`, kèm `saleOpensAt`. Phần chặn đơn đã có sẵn ở `server/app.js:269`, đếm ngược và nút "Sắp mở bán" đã có ở `EventHero`/`EventPage`.
- `finalize` (`src/lib/events.js`): phải **chuyển `saleOpensAt` từ chuỗi về `Date`**, vì dữ liệu đi qua JSON. Nếu không, `EventHero` gọi `.getTime()` lên một chuỗi và trang bị lỗi.

### 4.4 Form tạo sự kiện
- Thêm ô **"Mở bán lúc"** (`datetime-local`, không bắt buộc). Để trống thì mở bán khi được duyệt.
- Server kiểm tra: đúng định dạng và phải trước giờ bắt đầu diễn. Không bắt buộc phải sau thời điểm hiện tại, vì ở quá khứ thì cũng chỉ có nghĩa là mở ngay khi duyệt.
- Múi giờ: client gửi `YYYY-MM-DDTHH:mm`, server gắn `+07:00` khi lưu.

### 4.5 API
- `GET /organizer/me`: mỗi sự kiện thêm `phase`, `saleOpensAt`, `reviewedAt`.
- **Mới** `GET /organizer/stats?days=7` (days từ 1 đến 31): trả về `{ days: [{ date: 'YYYY-MM-DD', label: 'T2'|…|'CN', revenue, tickets }] }`.
  - Luôn đủ N ngày, ngày nào không có đơn thì ghi 0, sắp xếp từ cũ đến mới.
  - Gộp theo **ngày giờ Việt Nam** (`date(o.created_at, '+7 hours')`). Khoảng N ngày kết thúc ở hôm nay (giờ VN, tính cả hôm nay). Chỉ tính đơn thuộc sự kiện của Ban tổ chức đang đăng nhập. `revenue` là `SUM(orders.total)`, `tickets` là `SUM(order_items.qty)`. Hai tổng này phải tính bằng hai truy vấn con riêng, nếu JOIN chung thì `total` sẽ bị cộng lặp theo số dòng vé.
  - Trả cả hai số trong một lần, nên bấm đổi tab không phải gọi lại server.
- **Mới** `GET /organizer/events/:id`: chỉ chủ sự kiện xem được, người khác nhận 404.
  - `tiers`: `[{ id, name, price, capacity, sold, revenue }]`. `sold`/`revenue` lấy từ `order_items` theo `tier_id`. `capacity` là `remaining` trong `tiers_json`, vì sự kiện của Ban tổ chức chưa trừ kho vào `tiers_json`.
  - `timeline`: `{ createdAt, reviewedAt, saleOpensAt, startsAt }`.
  - `money`: `{ gross, discount, revenue, fee, net, orders }`. `revenue = SUM(total)`, `fee = revenue × 5%` (`FEE_RATE`), `net = revenue − fee`.
  - `recentOrders`: 5 đơn mới nhất của sự kiện.

### 4.6 Giao diện (cách A)
**Hook mới** (`src/hooks/`)
- `useOrganizerData()`: gọi `/organizer/me` và `/organizer/stats` song song, tự làm mới mỗi 15 giây (chuyển logic đang có trong `OrganizerDesk` sang đây). Trả về `{ data, stats, error, reload }`.
- `useEventDetail(id)`: chỉ gọi khi `id` có giá trị. Giữ kết quả đã tải trong một `Map` theo id để mở lại không phải chờ. Làm mới khi `useOrganizerData` làm mới.

**State trong `OrganizerDesk`**
- `mode`: `'rev' | 'tickets'` (đã có).
- `filter`: đọc và ghi qua URL `?loc=` (`tat-ca | dang-ban | sap-mo-ban | cho-duyet | da-dien`, mặc định `tat-ca`) bằng `useSearchParams`.
- `openId`: id sự kiện đang mở ngăn kéo, hoặc `null`. Mỗi lúc chỉ mở một sự kiện. Nếu sự kiện đang mở bị lọc mất thì đóng ngăn kéo.
- Danh sách đã lọc và số đếm mỗi tab: dùng `useMemo` trên `data.events`.

**Biểu đồ**: `BarChart` nhận `stats.days`, `valueKey` = `revenue` hoặc `tickets`. Doanh thu hiển thị dạng rút gọn (`compact`). Cần sửa `BarChart`:
- Dùng `key` là `date` thay cho `day`.
- Khi tất cả bằng 0 thì `max` bằng 0, công thức `v / max` ra NaN. Phải chặn trường hợp này và hiện trạng thái trống.

**Ngăn kéo** (mở rộng ngay tại dòng, có nút ▾, `aria-expanded`)
- Mốc thời gian: Gửi → Duyệt → Mở bán → Diễn, kèm đếm ngược tới mốc kế tiếp (`useCountdown` đã có).
- Theo loại vé: tên, giá, đã bán/tổng, thanh `Progress`, doanh thu.
- Tiền: doanh thu, phí sàn 5%, thực nhận, số đơn.
- 5 đơn gần đây.
- Nút "Mở trang sự kiện" và "Sao chép link" (chỉ khi đã duyệt).
- Theo `phase`: `rejected` thì chỉ hiện lý do và mốc thời gian. `upcoming-sale` thì đếm ngược tới giờ mở bán, chưa có phần đơn. `pending` thì chỉ hiện mốc thời gian.

**Con dấu / màu**: `STATUS` đổi sang khoá theo `phase`, thêm `upcoming-sale` (nhãn "Sắp mở bán"). Bỏ phép tính `ended` trên client, dùng `phase` từ server.

**Thẻ thống kê**: "Đang bán" đếm theo `phase === 'on-sale'`. Sức chứa/lấp đầy tính trên các sự kiện `on-sale` cộng `upcoming-sale`.

### 4.7 Dọn dẹp
- `src/data/dashboards.js`: `organizer.week` không còn dùng thì xoá. `status: 'upcoming'` trong dữ liệu mẫu đổi sang chữ "Sắp mở bán" nếu còn được dùng.
- Gói `ban-giao/` đã cũ từ trước. Lần này không cập nhật (có thể làm riêng khi người dùng yêu cầu).

## 5. Ràng buộc
- React 19 + Vite + Tailwind v4, Express 5 + `node:sqlite`, Node ≥ 22.13.
- File trong `src/lib`, `src/data` mà server import phải dùng import tương đối có `.js`.
- Thư mục dự án nằm dưới đường dẫn Unicode dạng NFD ("Tài liệu"). Khi tạo file phải kiểm tra không sinh ra thư mục trùng.
- Dự án **chưa có git** và **chưa có bộ test**. Kiểm chứng bằng cách gọi API thật (curl) và chạy `npm run build`.

## 5b. Quyết định nhỏ do Claude tự đưa ra (người dùng có thể sửa)
- **Múi giờ:** mọi so sánh thời gian ("đã diễn", giờ bắt đầu, `sale_start`) do server làm theo giờ +07:00. Trước đây quy tắc "đã diễn" chạy trên trình duyệt theo giờ máy người xem.
- **Độ trễ trạng thái:** khi đếm ngược tới giờ mở bán về 0, con dấu trên dashboard có thể chậm tối đa 15 giây (chu kỳ tự làm mới). Trang khách vẫn mở nút mua đúng giờ nhờ đếm ngược sẵn có.
- **Mục "Mới lên sàn" ở trang chủ:** sự kiện đã duyệt nhưng chưa mở bán vẫn hiện ở đó, và trang sự kiện hiển thị đếm ngược.
- Ô "Mở bán lúc" để trống thì mở bán khi được duyệt. Tab "Chờ duyệt" gộp cả "Bị trả lại". Ngăn kéo mở rộng tại dòng, mỗi lúc một sự kiện. Tab lọc lưu trên URL.

## 6. Để lại cho người dựng
- Bố cục và màu chi tiết của ngăn kéo (theo phong cách vé giấy, viền đậm hiện có).
- Cách tách component (`EventDrawer` có thể tách ra `src/components/dashboard/`).
- Thông báo lỗi tiếng Việt cho các trường hợp kiểm tra mới.
