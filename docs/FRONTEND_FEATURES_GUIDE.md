# TicketNhịp — Bản đồ tính năng Frontend

Tài liệu này liệt kê **toàn bộ tính năng giao diện** của TicketNhịp theo ba nhóm: đã xong, đang làm, sắp làm. Mỗi tính năng ghi rõ màn hình hoặc component nằm ở đâu, có những nút, form, bảng và trạng thái nào, và gọi API nào. Dùng tài liệu này làm "kim chỉ nam" khi tự thiết kế lại giao diện: giữ nguyên **hợp đồng dữ liệu** (API và trạng thái), còn bố cục, màu sắc, chữ và component thì tuỳ ý thay.

> Cập nhật: 2026-11-08, sau Task F4 của plan (phần máy chủ) `docs/plans/2026-11-07-organizer-dashboard-phase-2.md`.
> Mọi API đều có tiền tố `/api`. Frontend gọi qua `api(path, { method, body })` trong `frontend/src/services/api.js`; lỗi luôn có dạng `{"error": "<câu tiếng Việt>"}` và hiện thẳng câu đó cho người dùng.

---

## 0. Trước khi custom: những thứ dùng chung

### 0.1 Bản đồ đường dẫn

| URL | Trang (`frontend/src/pages/`) | Ai dùng |
|---|---|---|
| `/` | `HomePage.jsx` (bộ lọc danh mục / từ khoá giữ trong state của `App.jsx`, không nằm trên URL) | Khách |
| `/su-kien/:slug` | `EventPage.jsx` | Khách |
| `/su-kien/:slug/dat-ve?suat=<mã suất>` | `BookingPage.jsx` | Khách đã đăng nhập |
| `/ve-cua-toi` | `MyTicketsPage.jsx` | Khách đã đăng nhập |
| `/dieu-khoan-su-dung`, `/chinh-sach-bao-mat`, `/chinh-sach-doi-tra` (khai báo trong `frontend/src/constants/policies.js`) | `PolicyPage.jsx` | Mọi người |
| `/ban-to-chuc` | `OrganizerDashboard.jsx` | Vai trò `organizer` |
| `/quan-tri` | `AdminDashboard.jsx` | Vai trò `admin` |
| `*` | `NotFoundPage.jsx` | — |

### 0.2 Nơi đặt "giao diện" để sửa

| Muốn đổi | Sửa ở |
|---|---|
| Màu, font, bóng đổ, bo góc (design token) | `frontend/src/styles/index.css` (khối `@theme` của Tailwind v4: `ink`, `cream`, `paper`, `tomato`, `mustard`, `cobalt`, `forest`, `sand`, `shadow-hard*`…) |
| Nút, khung, tab, toast, ô ảnh giữ chỗ | `frontend/src/components/common/` (`Button`, `Container`, `Section`, `Tabs`, `Toast`, `ImagePlaceholder`, `ScrollRow`, `IconButton`, `LoadError`, `Logo`) |
| Khung bảng điều khiển (sidebar, tiêu đề, menu) | `frontend/src/components/layout/DashboardShell.jsx` |
| Thẻ số liệu, con dấu trạng thái, panel, tab chuyển, biểu đồ cột, thanh tiến độ, bục vinh danh | `frontend/src/components/common/widgets.jsx` (`StatCard`, `Stamp`, `Panel`, `Toggle`, `BarChart`, `Progress`, `Leaderboard`) |
| Nhãn + màu trạng thái đơn / sự kiện (dùng chung 3 giao diện) | `frontend/src/utils/status.js` |
| Tab lọc sự kiện của Ban tổ chức, chữ trên con dấu | `frontend/src/utils/dashboard.js` |
| Định dạng tiền | `frontend/src/utils/format.js` (`formatVND`) |

**Những chi tiết đang mang "chữ ký" của bản thiết kế hiện tại** (nên đổi nếu muốn giao diện mang dấu ấn riêng): con dấu nghiêng `-rotate-3` (`Stamp`), viền đen 2px kèm bóng đổ cứng `shadow-hard`, giấy nhắc việc xoay nghiêng trên bàn làm việc Admin (`StickyNote`), nhãn `font-mono` viết hoa giãn chữ (eyebrow), mép vé răng cưa và cuống vé (`ETicket`), chữ tiêu đề kiểu "sổ cái" ("đây là sổ cái của bạn", "In một xấp vé mới.").

### 0.3 Trạng thái phải hiển thị (lấy từ API, đừng tự tính)

**Đơn hàng** (`orders.status`, nhãn ở `frontend/src/utils/status.js` → `orderStatus()`):

| Giá trị | Nhãn | Màu gợi ý |
|---|---|---|
| `paid` | Đã trả | xanh lá |
| `refunded` | Đã hoàn | đỏ cam |
| `cancelled` | Đã huỷ | xám |
| khác | hiện nguyên chữ, màu xám (không bao giờ hiện "Đã trả") | |

**Sự kiện** (`phase` do máy chủ tính, nhãn ở `STATUS` trong `frontend/src/utils/status.js`):

| `phase` | Nhãn | Ý nghĩa | Sửa được? |
|---|---|---|---|
| `pending` | Chờ duyệt | BTC đã gửi, sàn chưa duyệt | sửa toàn bộ |
| `rejected` | Bị trả lại | kèm `rejectReason` | sửa toàn bộ, sửa xong quay về chờ duyệt |
| `upcoming-sale` | Sắp mở bán · dd/MM HH:mm | đã duyệt, chưa tới `saleOpensAt` | sửa giới hạn |
| `on-sale` | Đang bán | | sửa giới hạn |
| `closed` | Đang diễn | suất cuối đã bắt đầu, chưa qua ngày | không |
| `ended` | Đã diễn | đã qua ngày của suất cuối | không |
| `cancelled` | Đã huỷ | kèm `cancelReason`, `cancelledBy` (`organizer` / `admin`) | không |

**Mỗi màn hình có dữ liệu đều cần đủ 3 trạng thái:** đang tải ("Đang tải…"), rỗng (câu báo cụ thể), và lỗi (hiện `error.message` của API). Học phần chấm điểm phần này.

---

## 1. Tính năng ĐÃ HOÀN THÀNH

### 1.1 Tài khoản: đăng ký, đăng nhập, quên và đặt lại mật khẩu

- **UI:** `frontend/src/components/auth/AuthModal.jsx` (hộp thoại 4 bước), `AuthButton.jsx` (nút ở header), `AuthProvider.jsx` (giữ phiên), `LoginGate.jsx` (khối "Đăng nhập để…"), `fields.jsx` (ô nhập dùng chung). Khối đăng nhập / cấm truy cập của dashboard nằm ở `frontend/src/components/layout/Access.jsx` (`SignInScreen`, `ForbiddenScreen`, `FullLoader`, `AccountRow`).
- **Form:**
  - Đăng nhập: email hoặc SĐT, mật khẩu, nút "Tiếp tục" (khi đang gửi: "Đang đăng nhập…").
  - Đăng ký: họ tên, email hoặc SĐT, mật khẩu (tối thiểu 6 ký tự), nhập lại mật khẩu, nút "Tạo tài khoản".
  - Quên mật khẩu: email hoặc SĐT, nút "Gửi liên kết khôi phục".
  - Đặt lại mật khẩu: mật khẩu mới và nhập lại.
- **Trạng thái:** lỗi dưới từng ô (bỏ trống, mật khẩu không khớp), lỗi từ API (sai mật khẩu, bị khoá tạm vì nhập sai nhiều lần), nút bị khoá trong lúc gửi.
- **API:** `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/forgot`, `POST /auth/reset`. Phiên lưu trong cookie httpOnly `tn_session`, frontend không tự lưu token.

### 1.2 Trang chủ và tìm kiếm

- **UI:** `HomePage.jsx` gồm các khối trong `frontend/src/components/sections/`: `HeroBanner`, `FeaturedEvents`, `TrendingEvents`, `CategoryRow` (mỗi danh mục một hàng), `StarBadges`, `PosterBoard`, `ResaleMarket`, `MemberPasses`, `CouponBanner`, `WeekendSchedule`, `CityExplorer`, `CommunityEvents` (sự kiện của BTC), `BlogSection`, `FilterResults` (kết quả khi đang lọc danh mục hoặc tìm từ khoá). Thẻ sự kiện nằm ở `frontend/src/components/cards/` (`EventCard`, `TicketCard`, `PosterCard`, `SquareEventCard`, `TrendingCard`, `ResaleCard`, `Postcard`, `MemberPass`, `StarBadge`). Header ở `frontend/src/components/layout/header/` (`SearchBar`, `CategoryBar`, `MobileMenu`, `LanguageSwitcher`).
- **Hiển thị:** tên, ngày giờ, địa điểm, giá từ, trạng thái bán (`status`: `coming` = sắp mở bán kèm giờ mở, `on-sale`), số vé đang bán lại.
- **API:** `GET /home` (đủ các khu của trang chủ), `GET /events?q=&category=&city=&organizer=&sort=&limit=`, `GET /categories`.
- ⚠ **Lưu ý cho học phần ("không dùng mock data trong giao diện"):** một số khối vẫn lấy nội dung tĩnh từ `frontend/src/constants/` (`BlogSection`, `CityExplorer`, `MemberPasses`, `StarBadges`, `CouponBanner`, `WeekendSchedule`, menu/footer). Khi thiết kế lại, nên bỏ hoặc chuyển các khối này sang dữ liệu thật.

### 1.3 Trang sự kiện

- **UI:** `EventPage.jsx`, `frontend/src/components/event/EventHero.jsx` (khối đầu trang: giá từ, nút mua, lưu, chia sẻ, nhắc khi mở bán), `EventSections.jsx` (`EventAbout`, `TicketInfo` là lịch diễn kèm bảng giá theo suất, `OrganizerInfo`), thanh mục con dính đầu trang, sidebar mã giảm giá, thanh mua vé cố định trên mobile, khối "Có thể bạn cũng thích".
- **Nút và trạng thái:**
  - "Mua vé ngay": 1 suất thì mua ngay; nhiều suất thì cuộn tới phần lịch diễn.
  - "Đã bán hết vé" khi `soldOut = true`. Máy chủ xét mọi suất còn mở, nên một suất hết nhưng suất khác còn vé thì vẫn mua được.
  - "Sắp mở bán" kèm đồng hồ đếm ngược tới `saleOpensAt`.
  - Suất đã bắt đầu (`shows[*].closed = true`) hiện "ĐÃ DIỄN" và không có nút mua.
  - Số vé còn lại theo hạng lấy theo suất còn mở đầu tiên.
- **API:** `GET /events/{slug}` (có `shows[*].closed`, `soldOut`, `maxPerOrder`, `tiers[*].remaining`, `layout`, `map`), `GET /events/{slug}/availability?show=` (số vé còn lại theo hạng, và `unavailableSeats` với sự kiện bán theo ghế).

### 1.4 Đặt vé và thanh toán

- **UI:** `BookingPage.jsx`, `frontend/src/components/booking/`:
  - `BookingParts.jsx`: `Steps` (thanh 3 bước Chọn vé → Thanh toán → Hoàn tất), `Stepper` (nút −/+ số lượng), `ShowPicker` (chọn suất; suất đã diễn bị khoá và ghi "Đã diễn"), `Summary` (tóm tắt đơn).
  - `TicketPickers.jsx` + `ZoneMap.jsx` / `SeatMap.jsx` / `MapCanvas.jsx`: chọn theo loại vé, theo khu hoặc theo ghế.
  - `PaymentStep.jsx`: thông tin người nhận, phương thức thanh toán, mã giảm giá, đồng hồ giữ vé.
- **Form và nút:**
  - Bước 1: số lượng theo hạng (giới hạn bởi `event.maxPerOrder`, hiện là 10), hoặc chọn khu / ghế trên sơ đồ, nút "Tiếp tục · N vé".
  - Bước 2: họ tên, email, SĐT người nhận; 3 phương thức `qr` / `wallet` / `card`; ô "Mã giảm giá" và nút "Áp dụng"; nút "Thanh toán". Giữ vé 15 phút (`HOLD_MINUTES`), hết giờ thì quay lại bước 1.
  - Bước 3: vé điện tử vừa tạo.
- **Trạng thái:** ghế đã bán bị khoá; khi quá số vé tối đa thì báo "Mỗi đơn tối đa N vé"; mã giảm giá đúng / sai / chưa đủ giá trị đơn tối thiểu; sự kiện chưa mở bán thì hiện "Sự kiện chưa mở bán"; chưa đăng nhập thì hiện `LoginGate`.
- **API:** `GET /maps/{id}` (sơ đồ khu / ghế), `GET /events/{slug}/availability?show=`, `GET /coupons/{code}`, `POST /orders` với body `{slug, showId, items | seats, coupon?, method, buyer}`. Máy chủ tự tính giá, trừ kho và giữ ghế, nên frontend không gửi giá.

### 1.5 Vé của tôi

- **UI:** `MyTicketsPage.jsx`, `frontend/src/components/booking/ETicket.jsx` (mỗi đơn một vé: thông tin sự kiện, rồi từng cuống vé có QR và mã check-in), `QrCode.jsx`, `OrdersProvider.jsx` (giữ danh sách đơn).
- **Tab:** "Sắp diễn ra" / "Đã qua".
- **Trạng thái mỗi vé:** "Chưa check-in · hợp lệ", hoặc "Đã check-in lúc HH:mm dd/MM" (giờ soát thật lấy từ cổng).
- **Hành vi:** tải lại danh sách khi mở trang và mỗi lần quay lại tab trình duyệt, để thấy ngay vé vừa được soát hoặc đơn vừa bị hoàn.
- **API:** `GET /orders`. Mỗi đơn có `status`, `refundedAt`, `eventStatus`, `cancelReason`, `cancelledBy`, `tickets[*].checkedInAt`, `tickets[*].seat`.

### 1.6 Ban tổ chức: bàn làm việc ("Sổ cái hôm nay") và tạo sự kiện

- **UI:** `OrganizerDashboard.jsx` (bên trong là `OrganizerDesk`, `CreateEventForm`, ngăn kéo chi tiết sự kiện `DrawerDetail`), dùng khung `DashboardShell`. Dữ liệu lấy qua `frontend/src/hooks/useOrganizerData.js` (tự làm mới mỗi 15 giây) và `useEventDetail.js`.
- **Menu bên trái:** Sổ cái hôm nay · Tạo sự kiện mới · Sự kiện của tôi · Hoá đơn & đơn hàng · Báo cáo doanh thu · Soát vé tại cổng. Dưới cùng là khối "Số dư khả dụng" (hiện tính tạm ở giao diện, Task E sẽ làm thật).
- **Màn sổ cái:**
  - 4 thẻ số liệu: tổng doanh thu, vé đã bán, tỉ lệ lấp đầy, số sự kiện đang bán.
  - Biểu đồ 7 ngày, chuyển giữa Doanh thu và Số vé.
  - Danh sách sự kiện có 6 tab lọc qua `?loc=`: `tat-ca`, `dang-ban`, `sap-mo-ban`, `cho-duyet`, `da-dien`, `da-huy`.
  - Mỗi sự kiện có con dấu phase; bấm vào thì mở ngăn kéo chi tiết.
  - Ngăn kéo chi tiết: bảng hạng vé (giá, sức chứa, đã bán, doanh thu); tiền (gộp, giảm giá, doanh thu, phí sàn 5%, thực nhận); mốc thời gian (tạo, duyệt, mở bán, diễn); 5 đơn mới nhất.
- **Form "Tạo sự kiện mới":**
  - Tên, danh mục, thành phố, địa điểm, địa chỉ, ngày diễn, giờ bắt đầu, giờ kết thúc, giới thiệu (tách đoạn bằng dòng trống), "Mở bán lúc" (không bắt buộc).
  - Danh sách 1–8 loại vé (tên, giá 10.000–100.000.000 ₫, số lượng, quyền lợi) với nút thêm / xoá loại vé.
  - Lỗi từ máy chủ hiện ngay trong form.
- **Đăng ký làm Ban tổ chức** (khách thường): tên đơn vị, SĐT, giới thiệu.
- **API:** `GET /organizer/me` (hồ sơ, sự kiện kèm `phase`, `sold`, `capacity`, `revenue`, `saleOpensAt`, `cancelReason`, `cancelledBy`; đơn mới), `GET /organizer/stats?days=7`, `GET /organizer/events/{id}` (chi tiết, giờ có thêm `form` và `editable`, xem mục 1.12), `POST /organizer/events`, `POST /organizer/register`.

### 1.7 Ban tổ chức: Hoá đơn & đơn hàng

- **UI:** `frontend/src/pages/Organizer/components/OrdersView.jsx`, hook `frontend/src/hooks/useOrgOrders.js`.
- **Bộ lọc:**
  - ô tìm "Tìm mã đơn, tên, email, SĐT" (chờ 300 ms sau khi ngừng gõ mới gửi);
  - chọn sự kiện;
  - tab trạng thái: Tất cả, Đã trả, Đã hoàn, Đã huỷ;
  - "Từ ngày" / "Đến ngày".
  - Đổi bất kỳ bộ lọc nào thì quay về trang 1.
- **3 thẻ số liệu:** Đơn đã thanh toán, Doanh thu đã thu, Vé đã bán (tính trên toàn bộ kết quả lọc, không chỉ trang đang xem).
- **Danh sách đơn:** mã đơn và giờ mua, người mua (tên, email, SĐT), sự kiện, loại vé ("VIP ×1"), số vé đã soát trên tổng số vé, tổng tiền, con dấu trạng thái.
- **Phân trang:** "Trang trước" / "Trang sau" và "Trang X / N". Không có kết quả thì hiện "Không có đơn nào khớp bộ lọc".
- **API:** `GET /organizer/orders?q&eventId&status=all|paid|refunded|cancelled&from&to&page&pageSize` → `{orders[], page, pageSize, total, summary{paidOrders, paidRevenue, tickets}}`. Mỗi đơn có `refundedAt`.

### 1.8 Ban tổ chức: Báo cáo doanh thu

- **UI:** `frontend/src/pages/Organizer/components/ReportsView.jsx`, hook `frontend/src/hooks/useOrgReport.js`.
- **Điều khiển:**
  - khoảng nhanh "7 ngày", "30 ngày" (mặc định), "90 ngày", "Tuỳ chọn" (hiện thêm 2 ô ngày);
  - gom nhóm Ngày / Tuần / Tháng;
  - chọn sự kiện.
- **4 thẻ số liệu:** Doanh thu, Phí sàn, Thực nhận, Vé bán. Thêm một dòng "Không tính N đơn đã hoàn · X ₫".
- **Biểu đồ cột:** một chuỗi số liệu, chuyển giữa Doanh thu và Số vé. Khi có nhiều cột thì nhãn trục được rút bớt và chỉ cột cao nhất hoặc cột đang rê chuột hiện số.
- **Bảng "Theo sự kiện":** sự kiện, vé, doanh thu, phí sàn, thực nhận.
- **Bảng "Theo hạng vé":** hạng, sự kiện, giá, thanh tiến độ "đã bán / sức chứa", doanh thu.
- **Rỗng:** "Chưa có doanh thu trong khoảng này".
- **API:** `GET /organizer/reports?from&to&eventId&groupBy=day|week|month` → `{range, totals{gross, discount, revenue, fee, net, orders, tickets, refundedOrders, refundedAmount}, series[{key, label, revenue, tickets, orders}], byEvent[], byTier[]}`.

### 1.9 Ban tổ chức: Soát vé tại cổng (quét QR)

- **UI:** `frontend/src/pages/Organizer/components/GateView.jsx`, `QrScanner.jsx` (camera, nạp thư viện `qr-scanner` khi cần).
- **Nhập mã:**
  - ô "Mã vé" luôn được focus lại sau mỗi lần soát, nhận cả mã từ máy quét cầm tay gõ vào kèm Enter;
  - nút "Soát vé";
  - nút "Bật camera" / "Tắt camera". Không mở được camera thì hiện "Không mở được camera — hãy nhập mã".
- **Thẻ kết quả:**
  - xanh "HỢP LỆ";
  - vàng "ĐÃ SOÁT LÚC HH:mm" (vé đã soát trước đó, kèm giờ soát đầu tiên);
  - đỏ "KHÔNG HỢP LỆ" kèm câu lỗi.
  - Thẻ hiện mã, hạng vé, ghế, người mua, mã đơn, sự kiện.
  - Thêm cảnh báo "Vé không phải suất hôm nay" nếu sai ngày (chỉ cảnh báo, không chặn).
- **Thanh tiến độ** "N/M vé đã soát" của suất, và danh sách "Lượt soát gần đây" (10 lượt).
- **Hành vi:** trong lúc chờ máy chủ trả lời thì bỏ qua mã quét trùng.
- **API:** `POST /organizer/checkin` với `{code}` → `{result: "checked-in"|"already", ticket{…, checkedInAt}, showToday, progress{checkedIn, total}}`. Lỗi: 400 mã sai định dạng, 404 không tìm thấy vé, 409 vé thuộc đơn đã hoàn hoặc đã huỷ.

### 1.10 Quản trị sàn (Admin)

- **UI:** `AdminDashboard.jsx` (bàn làm việc), `frontend/src/pages/Admin/components/`:
  - `AdminOrders.jsx`: sổ đơn toàn sàn, dùng lại `OrdersView` với `scope="admin"` và thêm ô chọn "Ban tổ chức".
  - `OrganizersView.jsx`: danh sách Ban tổ chức, bấm một BTC để xem sự kiện của họ.
  - `TicketLookup.jsx`: tra mã vé, chỉ xem.
  - Trang "Báo cáo doanh thu" dùng lại `ReportsView` với `scope="admin"`.
- **Menu:** Bàn làm việc · Duyệt sự kiện · Ban tổ chức · Sổ đơn hàng · Báo cáo doanh thu · Tài chính & rút tiền (Task E).
- **Bàn làm việc:**
  - 3 giấy nhắc việc: số hồ sơ chờ duyệt, số Ban tổ chức, số sự kiện đã lên sàn;
  - 4 thẻ số liệu: doanh thu toàn sàn kèm phí sàn và phần sàn tự bán, vé đã bán, hồ sơ chờ duyệt, khách hàng;
  - biểu đồ 6 tuần (Doanh thu / Số vé);
  - "Bục vinh danh" top 5 sự kiện;
  - hồ sơ chờ đóng dấu với nút "Duyệt" / "Trả lại" kèm lý do;
  - sổ đơn và ô tra mã vé. Kết quả tra mã vé hiện "Chưa soát", "Đã soát lúc…", "Đơn đã hoàn" hoặc "Đơn đã huỷ", kèm nút "Xem đơn trong sổ".
- **API:** `GET /admin/overview` (`pending[]`, `totals{revenue, orgRevenue, platformRevenue, fee, orders, tickets, customers, organizers, approvedEvents}`), `POST /admin/events/{id}/review` với `{decision: approve|reject, reason}`, `GET /admin/orders` (như sổ đơn BTC, thêm `organizerId`, mỗi đơn có `orgName`, `null` nghĩa là sàn tự bán), `GET /admin/organizers`, `GET /admin/organizers/{id}/events`, `GET /admin/reports` (thêm `byOrganizer[]`, `totals.platformRevenue`), `GET /admin/tickets/{code}`.

### 1.11 Huỷ sự kiện và hoàn tiền: phần máy chủ (Task D1)

Đã có API và các thay đổi phía khách. Nút và hộp xác nhận cho Ban tổ chức sẽ làm ở D3 (mục 2.1).

- **Đã có trên giao diện:** tab "Đã huỷ" và con dấu "Đã huỷ" trên dashboard Ban tổ chức. Sự kiện đã huỷ biến mất khỏi trang chủ và trang tìm kiếm, mở trang sự kiện thì ra 404, không đặt vé được, vé của nó soát thì báo 409.
- **API:** `DELETE /organizer/events/{id}` với body `{reason}` (luôn gửi JSON). Chưa có đơn nào thì xoá hẳn, trả `{deleted: true}`. Có đơn thì huỷ và hoàn tiền, trả `{deleted: false, refundedOrders, refundedAmount, event}`. Lỗi: 400 thiếu lý do (cần 5–300 ký tự), 409 sự kiện đã diễn hoặc đã huỷ, 404 sự kiện của Ban tổ chức khác.

### 1.12 Sửa sự kiện: phần máy chủ (Task D2)

Đã có API. Form sửa trên giao diện làm ở D3 (mục 2.1).

- `GET /organizer/events/{id}` trả thêm:
  - `form`: giá trị hiện tại của form, mỗi loại vé có `id` và `sold`;
  - `editable`: `{mode: "full"|"limited"|"none", saleStart: bool}`.
- **Quy tắc giao diện cần phản ánh:**
  - `full` (chờ duyệt hoặc bị trả lại): mọi ô sửa được.
  - `limited` (đã duyệt, chưa diễn):
    - khoá các ô tên, danh mục, thành phố, địa điểm, ngày, giờ bắt đầu, giờ kết thúc;
    - "Mở bán lúc" chỉ sửa được khi `editable.saleStart` là true;
    - loại vé có `sold > 0` thì khoá giá, không cho xoá, và ô số lượng tối thiểu bằng `sold`;
    - được thêm loại vé mới.
  - `none`: ẩn nút "Sửa sự kiện".
- **API:** `PATCH /organizer/events/{id}` với body giống form tạo, loại vé cũ gửi kèm `id`, trả `{event}`. Lỗi: 409 sửa trường bị khoá, đổi giá hạng đã bán, bỏ hạng đã bán hoặc sự kiện không còn sửa được; 400 số lượng thấp hơn số đã bán.

---

## 2. Tính năng ĐANG và SẮP LÀM

### 2.1 Task D3: nút Sửa / Huỷ trên ngăn kéo sự kiện — ĐÃ XONG (2026-11-08)

- **UI:**
  - `OrganizerDashboard.jsx`: ngăn kéo có thêm nút "Sửa sự kiện" (ẩn khi `mode = none`) và nút "Huỷ sự kiện". `CreateEventForm` dùng lại cho việc sửa: điền sẵn `form`, nút đổi thành "Lưu thay đổi".
  - `frontend/src/pages/Organizer/components/CancelEventDialog.jsx` (mới): hiện số đơn và số tiền sẽ hoàn (`detail.money.orders`, `detail.money.revenue`); ô lý do (bắt buộc khi đã có đơn); phải gõ đúng tên sự kiện thì nút "Huỷ sự kiện" mới bật. Xong thì báo "Đã huỷ sự kiện và hoàn tiền N đơn".
  - **Phía khách** (`ETicket.jsx`, `MyTicketsPage.jsx`):
    - đơn `refunded` hiện con dấu "Sự kiện đã huỷ · Đã hoàn X ₫" và lý do huỷ;
    - ẩn QR và mã check-in, bỏ link tới trang sự kiện;
    - thêm tab "Đã huỷ", hai tab cũ chỉ còn đơn `paid`.
- **API:** `GET /organizer/events/{id}`, `PATCH /organizer/events/{id}`, `DELETE /organizer/events/{id}`, `GET /orders`.

### 2.2 Task D4: Admin gỡ sự kiện vi phạm — MÁY CHỦ ĐÃ XONG (2026-11-08), giao diện do nhóm tự làm

**API:** `POST /api/admin/events/{id}/cancel` — chỉ tài khoản `admin` (cookie phiên `tn_session`).

- **Request** (luôn gửi JSON, `Content-Type: application/json`):
  ```json
  { "reason": "Sự kiện vi phạm điều khoản của sàn" }
  ```
  `reason` bắt buộc, 5–300 ký tự (khác BTC: Admin cần lý do kể cả khi sự kiện chưa có đơn nào).
- **Response 200** — Admin **không bao giờ xoá hẳn** sự kiện (giữ dấu vết), `deleted` luôn `false`:
  ```json
  {
    "deleted": false,
    "refundedOrders": 2,
    "refundedAmount": 600000,
    "event": { "id": 12, "title": "…", "phase": "cancelled", "cancelReason": "…", "cancelledBy": "admin", "…": "các khoá còn lại như event_summaries" }
  }
  ```
  Mọi đơn `paid` của sự kiện chuyển `refunded` (có `refundedAt`) trong cùng một transaction với việc đổi trạng thái sự kiện.
- **Lỗi** (`{"error": "…"}`, hiện thẳng câu này):

  | Mã | Khi nào | Câu lỗi |
  |---|---|---|
  | 400 | thiếu / quá ngắn / quá dài lý do | `Vui lòng nhập lý do huỷ (5–300 ký tự)` |
  | 401 / 403 | chưa đăng nhập / không phải admin | — |
  | 404 | mã sự kiện sai định dạng hoặc không tồn tại | `Sự kiện không tồn tại` |
  | 409 | sự kiện đã huỷ trước đó (kể cả do BTC vừa huỷ cùng lúc) | `Sự kiện đã được huỷ trước đó` |
  | 409 | sự kiện đã diễn ra (`closed` / `ended`) | `Sự kiện đã diễn ra, không thể huỷ` |

- **Đồng thời:** Admin gỡ và BTC huỷ cùng lúc → chỉ một bên thành công (khoá dòng `FOR UPDATE`), bên kia nhận 409; đơn chỉ hoàn một lần. `cancelledBy` cho biết bên nào thắng.
- **Dữ liệu `cancelledBy`** (`"organizer"` | `"admin"` | `null`) có ở:
  - `GET /api/admin/organizers/{id}/events` → mỗi sự kiện (`cancelledBy`, `cancelReason`, `phase`);
  - `GET /api/organizer/me` / chi tiết sự kiện của BTC (cùng `event_summaries`);
  - `GET /api/orders` của khách → mỗi đơn (`status`, `eventStatus`, `cancelReason`, `cancelledBy`, `refundedAt`).

**Giao diện cần làm (gợi ý, nhóm tự thiết kế):**
- **Admin — danh sách sự kiện của một BTC:** nút "Gỡ sự kiện" chỉ hiện khi `phase ∈ {pending, rejected, upcoming-sale, on-sale}`. Hộp xác nhận: ô lý do (bắt buộc, đếm 5–300 ký tự), nút gửi bị vô hiệu khi lý do chưa hợp lệ.
  - *Đang gửi:* khoá nút, hiện "Đang gỡ…".
  - *Thành công:* toast "Đã gỡ sự kiện và hoàn tiền N đơn" (N = `refundedOrders`), tải lại danh sách.
  - *400:* hiện lỗi dưới ô lý do. *409:* hiện câu lỗi trong hộp, tải lại danh sách (sự kiện có thể vừa bị BTC huỷ). *404:* đóng hộp, tải lại.
- **Dashboard BTC:** sự kiện `cancelledBy == "admin"` → con dấu "Sàn đã gỡ" + `cancelReason` (khác "Đã huỷ" khi BTC tự huỷ).
- **Vé của tôi:** đơn `refunded` có `cancelledBy == "admin"` → "Sàn đã gỡ sự kiện · Đã hoàn X ₫" thay cho "Sự kiện đã huỷ"; ẩn QR / mã check-in.
- **Postman:** thư mục "7 · Quản trị sàn — vận hành" → "Gỡ sự kiện vi phạm…" và "Gỡ sự kiện — thiếu lý do (400)" (đặt biến `eventId`).

### 2.3 Task E: Rút tiền về ngân hàng — MÁY CHỦ ĐÃ XONG (E1, E2 — 2026-11-08), giao diện do nhóm tự làm

> CSDL dev cần chạy migration **0007** (`cd backend && .venv/Scripts/python.exe -m alembic upgrade head`) trước khi gọi các API này trên máy dev; chưa nâng thì API trả 500.

**Quy tắc tiền** (máy chủ tính, giao diện chỉ hiển thị — đừng tự tính):
- `settledNet` — thực nhận (doanh thu − phí sàn 5 %, phí tính riêng từng sự kiện) của các sự kiện **đã diễn xong** → chỉ phần này rút được.
- `held` — thực nhận của sự kiện chưa diễn (còn có thể bị huỷ và hoàn tiền) → "đang tạm giữ".
- `pending` — tổng các yêu cầu đang chờ Admin; `paid` — tổng đã chuyển. Yêu cầu bị từ chối trả tiền lại số dư.
- `available = settledNet − pending − paid` (không bao giờ âm).

#### E1 · Ban tổ chức (vai trò `organizer`)

**`GET /api/organizer/withdrawals`** → 200
```json
{
  "balance": { "settledNet": 570000, "held": 190000, "pending": 100000, "paid": 0, "available": 470000 },
  "withdrawals": [
    { "id": 3, "amount": 100000, "bankName": "Vietcombank", "accountNo": "0123456789",
      "accountName": "CONG TY SU KIEN", "status": "pending", "note": null,
      "createdAt": "2026-11-08T10:15:00+07:00", "processedAt": null }
  ]
}
```
`withdrawals` mới trước. `status`: `pending` (Chờ xử lý) · `paid` (Đã chuyển) · `rejected` (Từ chối — `note` là lý do).

**`POST /api/organizer/withdrawals`** — body JSON:
```json
{ "amount": 100000, "bankName": "Vietcombank", "accountNo": "0123456789", "accountName": "CONG TY SU KIEN" }
```
→ **201** `{ "withdrawal": {…như trên}, "balance": {…số dư mới} }`

| Mã | Câu lỗi | Khi nào |
|---|---|---|
| 400 | `Số tiền rút tối thiểu 50.000 ₫` | `amount` không phải số nguyên hoặc < 50 000 |
| 400 | `Vui lòng nhập tên ngân hàng` | `bankName` thiếu / < 2 / > 60 ký tự |
| 400 | `Số tài khoản chỉ gồm 6–20 chữ số` | `accountNo` có ký tự khác chữ số 0–9 hoặc sai độ dài |
| 400 | `Vui lòng nhập tên chủ tài khoản` | `accountName` thiếu / < 2 / > 60 ký tự |
| 409 | `Số dư khả dụng không đủ` | `amount > available` (kể cả khi 2 yêu cầu gửi cùng lúc — máy chủ khoá dòng, chỉ 1 cái qua) |
| 401 / 403 | — | chưa đăng nhập / không phải Ban tổ chức |

**Gợi ý giao diện:**
- Khối số dư: "Số dư khả dụng" = `available`; dòng phụ "Đang tạm giữ: `held` ₫ — rút được sau khi sự kiện diễn xong"; có thể hiện "Chờ duyệt: `pending` ₫".
- Nút "Rút về ngân hàng" vô hiệu khi `available < 50000`.
- Hộp rút tiền: điền sẵn số tiền = `available`; kiểm tra ngay trên giao diện 50 000 ≤ số tiền ≤ `available`, số TK 6–20 chữ số.
  - *Đang gửi:* khoá nút. *201:* toast "Đã gửi yêu cầu rút X ₫", thay số dư bằng `balance` trả về, thêm dòng vào lịch sử.
  - *400:* hiện lỗi dưới ô tương ứng. *409:* hiện lỗi + tải lại `GET` (số dư đã đổi).
- Lịch sử: *đang tải* (skeleton) · *rỗng* ("Chưa có yêu cầu rút tiền nào") · *lỗi* (câu `error` + nút Thử lại). Con dấu theo `status`, dòng `rejected` hiện `note`.

#### E2 · Admin (vai trò `admin`)

**`GET /api/admin/withdrawals?status=pending|paid|rejected|all`** (mặc định `pending`) → 200
```json
{ "withdrawals": [ { "id": 3, "amount": 100000, "bankName": "…", "accountNo": "…", "accountName": "…",
  "status": "pending", "note": null, "createdAt": "…+07:00", "processedAt": null,
  "orgName": "Công ty Sự kiện", "organizerId": 12, "orgAvailable": 470000 } ] }
```
`pending` xếp **cũ trước** (hàng đợi); các trạng thái khác mới trước. `orgAvailable` = số dư khả dụng hiện tại của BTC (đã trừ cả yêu cầu đang chờ) để Admin đối chiếu. Lỗi: 400 `Trạng thái không hợp lệ`.

**`POST /api/admin/withdrawals/{id}/decide`** — body `{ "decision": "paid" | "rejected", "note": "…" }` → 200 `{ "withdrawal": {…, "orgName"} }`

| Mã | Câu lỗi | Khi nào |
|---|---|---|
| 400 | `Quyết định không hợp lệ` | `decision` khác `paid` / `rejected` |
| 400 | `Vui lòng nhập lý do từ chối (3–300 ký tự)` | từ chối mà thiếu / sai độ dài `note` |
| 404 | `Không tìm thấy yêu cầu rút tiền` | id sai định dạng hoặc không có |
| 409 | `Yêu cầu này đã được xử lý` | yêu cầu không còn `pending` (kể cả 2 Admin bấm cùng lúc — chỉ 1 người thắng) |

**Số liệu bổ sung:** `GET /api/admin/overview` thêm `pendingWithdrawals` (**số** yêu cầu đang chờ). `GET /api/admin/organizers` mỗi BTC thêm `available`, `held`, `pendingWithdrawals` (**số tiền** đang chờ, ₫) — trùng khớp với số BTC đó thấy ở `GET /organizer/withdrawals`.

**Gợi ý giao diện:** mục "Tài chính & rút tiền" — bộ lọc trạng thái; mỗi dòng: BTC, số tiền, ngân hàng/STK, `orgAvailable`, nút "Đã chuyển" / "Từ chối" (mở ô lý do). *409:* báo "Yêu cầu này đã được xử lý" và tải lại danh sách. Giấy nhớ trên bàn làm việc: "`pendingWithdrawals` yêu cầu rút tiền chờ xử lý". `OrganizersView`: cột Khả dụng / Tạm giữ / Chờ rút.

**Postman:** thư mục 6 ("Rút tiền — …", 3 request) và thư mục 7 ("Yêu cầu rút tiền chờ xử lý", "Duyệt rút tiền — …"; request đầu tự lưu biến `withdrawalId`).

### 2.4 Task G: hạng mục CSDL bắt buộc — MÁY CHỦ ĐÃ XONG (G1–G3, 2026-11-08), giao diện do nhóm tự làm

> CSDL dev cần nâng lên migration **0008** (`alembic upgrade head`: 0007 bảng rút tiền + 0008 chỉ mục) trước khi dùng các API dưới đây trên máy dev.

- **G1 · dữ liệu lớn** (`python -m app.seed_large`, xem `database/docs/du-lieu-lon.md`): giao diện không đổi. Trên bộ dữ liệu lớn (100 000 đơn), mọi bảng đều phải phân trang; không màn nào được tải toàn bộ danh sách.
- **G2 · chỉ mục** (`database/docs/hieu-nang.md`): giao diện không đổi. Ô tìm sổ đơn trên 100 000 đơn giảm từ ~83 ms xuống ~0,5 ms. Kết quả tìm vẫn y như cũ: mã đơn khớp **tiền tố**; tên, email, SĐT khớp "chứa".
- **G3 · 8 truy vấn SQL** (`database/docs/truy-van.md`). Hợp đồng API **chỉ thêm khoá**, không bỏ khoá nào:

  | API | Khoá mới | Ý nghĩa |
  |---|---|---|
  | `GET /api/organizer/reports`, `/api/admin/reports` → `series[*]` | `cumulative` (₫), `changePct` (số % 1 chữ số thập phân hoặc `null`) | doanh thu cộng dồn từ đầu khoảng; % so với mốc liền trước (`null` khi mốc trước = 0) |
  | … → `byEvent[*]` | `rank` (1, 1, 3… — bằng doanh thu thì cùng hạng), `percentRank` (0–1) | thứ hạng doanh thu trong khoảng |
  | … → `byTier[*]` | `revenueShare` (% doanh thu của hạng trong sự kiện), `fillRate` (% đã bán / sức chứa, kể cả bán sẵn) | |

  **Mới · `GET /api/organizer/top-customers?from=YYYY-MM-DD&to=YYYY-MM-DD`** (vai trò organizer; mặc định 30 ngày đến hôm nay; lỗi ngày → 400 như `/organizer/reports`) → 200
  ```json
  { "range": { "from": "2026-10-10", "to": "2026-11-08" },
    "customers": [ { "rank": 1, "userId": 51, "name": "Nguyễn Văn An", "email": "an@x.vn", "phone": "0912…",
                     "orders": 3, "tickets": 7, "spent": 2100000, "lastOrderAt": "2026-11-07T20:15:00+07:00" } ] }
  ```
  Top 10 **hạng**: dùng DENSE_RANK, khách chi bằng nhau thì cùng hạng, nên có thể nhiều hơn 10 dòng. Chỉ tính đơn `paid` của sự kiện thuộc Ban tổ chức này.

  **Mới · `GET /api/admin/events/stale?days=7`** (vai trò admin; `days` 1–90, sai → 400 `Số ngày không hợp lệ`) → 200
  ```json
  { "days": 7, "events": [ { "id": 12, "slug": "…", "title": "…", "organizerId": 5, "orgName": "…",
                             "saleOpensAt": "…+07:00", "startsAt": "…+07:00", "lastSaleAt": null } ] }
  ```
  Đây là các sự kiện đang mở bán (đã duyệt, đã tới giờ mở bán, suất cuối chưa bắt đầu) mà không có đơn `paid` nào trong `days` ngày qua. Sự kiện chưa bán được vé nào (`lastSaleAt: null`) đứng đầu.

**Gợi ý giao diện:**
- `ReportsView`: thêm cột "Luỹ kế" và "So với kỳ trước". `changePct` dương thì tô xanh kèm ▲, âm thì tô đỏ kèm ▼, `null` thì hiện "—". Thêm bảng "Khách mua nhiều nhất" với các trạng thái *đang tải* / *rỗng* ("Chưa có khách trong khoảng này") / *lỗi*.
- Bục vinh danh Admin: dùng `byEvent[*].rank`; nhiều sự kiện cùng hạng thì đứng chung bậc.
- Bàn làm việc Admin: thêm giấy nhắc "N sự kiện đang bán chưa có đơn 7 ngày", bấm vào thì mở danh sách.
- Postman: thư mục 6 có "Khách mua nhiều nhất"; thư mục 7 có "Sự kiện đang bán chưa có đơn 7 ngày" và request 400.

### 2.5 Task F: bán theo sơ đồ khu / ghế — MÁY CHỦ ĐÃ XONG (F1, F3, F4 — 2026-11-08), giao diện (F2 và phần UI của F3/F4) do nhóm tự làm

#### F1 · Ban tổ chức chọn sơ đồ có sẵn

**`GET /api/organizer/venue-maps`** (vai trò organizer) → 200
```json
{ "maps": [ { "id": "arena", "kind": "zones", "name": "Sân khấu Arena", "capacity": 9800,
              "groups": [ { "id": "fanzone", "label": "FANZONE", "color": "#…", "capacity": 1200,
                            "maxPerOrder": 4, "perks": "…" } ] } ] }
```
`kind`: `zones` (sơ đồ khu) hoặc `seats` (sơ đồ ghế). `groups[*].capacity` là tổng sức chứa các khu của nhóm, hoặc số ghế của nhóm. Nhóm được sắp theo thứ tự hiển thị của sơ đồ.

**`POST /api/organizer/events`** nhận thêm 3 khoá. Sự kiện `list` gửi như cũ.
```json
{ "...các trường cũ...": "", "layout": "zones", "mapId": "arena",
  "prices": { "fanzone": 2500000, "ga1": 1100000, "...": 0 } }
```
- `layout` ∈ `list | zones | seats` (mặc định `list`); giá trị khác → 400 `Kiểu bán vé không hợp lệ`.
- Với `zones` / `seats`:
  - `mapId` phải tồn tại và đúng loại, nếu không → 400 `Sơ đồ không hợp lệ`.
  - `prices` phải có giá cho **mọi** nhóm trong `groups`, mỗi giá 10 000–100 000 000; thiếu hoặc sai → 400 `Nhóm “<label>”: giá từ 10.000 ₫ đến 100.000.000 ₫`.
  - `tiers` bị bỏ qua.
- Máy chủ tự sinh hạng vé theo quy ước của sàn:
  - `zones`: mỗi khu một hạng (id = mã khu), có kho.
  - `seats`: mỗi nhóm ghế một hạng (id = mã nhóm), "đã bán" đếm theo ghế.
- Khách đặt vé như sự kiện của sàn: `items` theo mã khu, hoặc `seats` theo mã ghế.

#### F3 · Admin xem trước hồ sơ + chặn duyệt quá giờ

**`GET /api/admin/events/{id}`** (vai trò admin; sự kiện **mọi trạng thái**: chờ duyệt, bị trả lại, đã huỷ…) → 200
```json
{ "event": { "…": "CÙNG JSON với GET /api/events/{slug}", "related": [] },
  "summary": { "…": "như một dòng sự kiện ở dashboard (phase, sold, revenue…)" },
  "organizer": { "orgName": "…", "code": "ORG-00012", "email": "…", "phone": "…" } }
```
Lỗi 404 `Sự kiện không tồn tại`. Sự kiện do sàn tự bán thì `organizer` là `null`.

`POST /api/admin/events/{id}/review` có lỗi mới: duyệt (`approve`) khi suất đầu tiên đã bắt đầu → 409 `Đã qua giờ diễn, không thể duyệt`. Trả lại (`reject`) vẫn được.

**Gợi ý giao diện:** nút "Xem hồ sơ" trên thẻ chờ duyệt mở ngăn kéo toàn màn hình. Ngăn kéo dựng **đúng component trang sự kiện của khán giả** từ `event` (dùng `reviveEvent`):
- có dải "XEM TRƯỚC — CHƯA CÔNG KHAI";
- nút mua bị vô hiệu;
- sơ đồ ở chế độ chỉ xem;
- chỗ đặt các nút Duyệt / Trả lại / Gỡ sự kiện (D4).

Khi nhận 409: hiện lỗi và tải lại danh sách chờ duyệt.

#### F4 · Sửa sự kiện theo sơ đồ

`PATCH /api/organizer/events/{id}` nhận thêm `layout`, `mapId`, `prices`, giống lúc tạo. `GET /api/organizer/events/{id}` → `form` có sẵn `layout`, `mapId`, `prices`.

| Mức sửa (`editable.mode`) | Được làm | Lỗi |
|---|---|---|
| `full` (chờ duyệt / bị trả lại) | đổi tự do giữa `list` ⇄ `zones` ⇄ `seats`, đổi sơ đồ, đổi giá; máy chủ sinh lại hạng vé | 400 như lúc tạo |
| `limited` (đã duyệt, chưa diễn) — sự kiện theo sơ đồ | chỉ đổi giá của **nhóm chưa bán vé nào** | 409 `Sự kiện đã duyệt không thể đổi kiểu bán vé`, 409 `Sự kiện đã duyệt không thể đổi sơ đồ`, 409 `Nhóm “<label>” đã có người mua, không đổi được giá` |
| `limited` — sự kiện `list` | như D2 (không đổi sang sơ đồ được → 409 kiểu bán vé) | |

**Gợi ý giao diện (F2 + F4):**
- Form tạo / sửa có bộ chọn "Loại vé / Sơ đồ khu / Sơ đồ ghế".
- Khi chọn sơ đồ:
  - danh sách sơ đồ đúng loại;
  - mỗi nhóm một ô giá, kèm màu và sức chứa, cùng tổng sức chứa;
  - bên cạnh là **bản xem trước dùng chính component sơ đồ của khán giả**, giá lấy theo số đang nhập.
- Khi sửa ở mức `limited`: khoá phần chọn sơ đồ, khoá ô giá của nhóm đã bán (tổng `form.tiers[*].sold` của các hạng thuộc nhóm > 0).
- Chặn ngay trên giao diện khi thiếu giá: hiện "Nhập giá cho nhóm …".

**Postman:**
- Thư mục 6: "Sơ đồ khu / ghế có sẵn", "Tạo sự kiện theo sơ đồ khu" (tự lưu `eventId`).
- Thư mục 7: "Xem trước hồ sơ sự kiện".

---

## 3. Gợi ý khi tự custom giao diện

1. **Giữ hợp đồng, đổi trình bày.** Tên prop, đường dẫn API, các giá trị `status` / `phase` và nhãn trong `frontend/src/utils/status.js` là chung cho cả 3 giao diện. Muốn đổi chữ trên con dấu thì sửa một chỗ đó.
2. **Đổi token trước, đổi component sau.** Sửa bảng màu, font và bóng trong `frontend/src/styles/index.css`, rồi tới `frontend/src/components/common/` và `components/common/widgets.jsx`. Phần lớn các màn sẽ đổi theo mà không cần đụng logic.
3. **Test đọc chữ trên màn hình.** Vitest tìm phần tử theo nhãn và vai trò (vd. nút "Trang sau", ô "Mã vé", bảng "Theo hạng vé", chữ "Đã hoàn"). Nếu đổi câu chữ thì sửa test tương ứng trong `*.test.jsx`. Chạy `npm test` sau mỗi lần đổi.
4. **Đủ 3 trạng thái cho mọi màn có dữ liệu:** đang tải, rỗng, lỗi (học phần chấm). Mỗi màn lỗi nên có nút "Thử lại".
5. **Biểu đồ:** một biểu đồ một trục. Hai thước đo khác đơn vị (tiền và số vé) thì dùng nút chuyển hoặc hai biểu đồ riêng, không vẽ chung hai trục.
6. **Thiết kế cho điện thoại trước.** Cổng soát vé và "Vé của tôi" chủ yếu dùng trên điện thoại: nút to, chữ mã vé dễ đọc, thẻ kết quả nhìn từ xa vẫn thấy màu.
