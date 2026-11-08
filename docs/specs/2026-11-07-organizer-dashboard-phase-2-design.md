# Bảng điều khiển Ban tổ chức — giai đoạn 2 (thiết kế)

Ngày: 2026-11-07 · Trạng thái: đã chốt với người dùng · Tiếp nối: `2026-11-06-organizer-dashboard-live-data-design.md`

## Mục tiêu
Hoàn thiện 5 phần còn thiếu của `/ban-to-chuc`: Hoá đơn & đơn hàng, Báo cáo doanh thu, Soát vé tại cổng,
Sửa/Huỷ sự kiện, Rút tiền về ngân hàng. Mỗi phần = API FastAPI (pytest + Postman) + giao diện React, làm trọn
từng phần theo thứ tự trên (đọc trước, ghi/đụng tiền sau).

## Quyết định đã chốt
1. **Thứ tự:** theo từng tính năng (API → test → Postman → giao diện), 1 → 5 như trên.
2. **Huỷ sự kiện:** chưa có đơn nào → xoá hẳn. Có đơn → `events.status = 'cancelled'` (ẩn khỏi danh mục, ngừng bán),
   mọi đơn `paid` → `refunded`, bắt buộc lý do huỷ. Sự kiện đã diễn ra / đã huỷ → không huỷ được.
3. **Sửa sự kiện:**
   - `pending` / `rejected`: sửa toàn bộ như form tạo; `rejected` sửa xong → về `pending`, xoá lý do từ chối.
   - `approved` và chưa diễn: chỉ sửa giới thiệu, địa chỉ, giờ mở bán (chỉ khi chưa mở bán), tên/quyền lợi hạng vé,
     số lượng hạng vé (không thấp hơn số đã bán), giá hạng vé chưa ai mua, thêm hạng vé mới, bỏ hạng vé chưa ai mua.
     Đổi tên sự kiện / danh mục / thành phố / địa điểm / ngày giờ diễn → từ chối (409).
   - Đã diễn ra / đã huỷ: không sửa được (409).
4. **Rút tiền:** bảng `withdrawals` (pending → paid | rejected). Admin xác nhận đã chuyển / từ chối ở trang Quản trị.
   Cách tính số dư: xem quyết định 6.
5. **Hoàn tiền trong báo cáo** (chốt khi brainstorming bù): đơn hoàn được trừ vào **ngày mua**. Doanh thu chỉ gồm
   đơn `paid`, gom theo `created_at`, khớp biểu đồ Sổ cái và VIEW `v_daily_revenue`. Khối "Hoàn tiền" đếm riêng
   các đơn `refunded` có ngày mua trong khoảng báo cáo. Thêm cột `orders.refunded_at` chỉ để hiện ngày hoàn trong danh sách đơn.
6. **Số dư không bao giờ âm** (chốt khi brainstorming bù, thay cho cách "rút được ngay"):
   - **Đang tạm giữ** = thực nhận của các sự kiện chưa diễn xong.
   - **Khả dụng** = thực nhận của các sự kiện **đã diễn xong** − tổng yêu cầu rút `pending` + `paid`.
   - "Đã diễn xong" nghĩa là ngày (giờ VN) của suất cuối < hôm nay, đúng như `phase == 'ended'`.
   - Sự kiện đã diễn xong thì không huỷ được, nên khi huỷ chỉ tiền đang tạm giữ bị trừ, còn số dư khả dụng không đổi.
   - Thực nhận = doanh thu − phí 5%, tính phí theo **từng sự kiện**, khớp ngăn kéo sự kiện.
7. **Suất diễn:** sự kiện của BTC giữ **1 suất** (như form hiện tại). Đặt vé, soát vé và báo cáo vẫn viết theo `show_id`
   để sau này mở rộng mà không phải làm lại.

8. **BTC chọn sơ đồ có sẵn** (chốt sau khi quét UI khán giả): form tạo/sửa có bố trí `list` | `zones` | `seats`.
   Với sơ đồ: chọn một `venue_maps` cùng loại, BTC chỉ đặt **giá cho từng nhóm giá** của sơ đồ; hạng vé do máy chủ
   sinh đúng quy ước catalog (zones: mỗi khu một hạng `id = zone.id`, `group_id = zone.group_id`, kho `tier_stock`;
   seats: mỗi nhóm một hạng `id = group.id`, kho là `seat_holds`). Sức chứa lấy từ sơ đồ, BTC không sửa.
9. **Một nguồn số liệu "đã bán / còn lại"** cho cả khán giả, BTC, Admin: hàm `stock.tier_stats` (list/zones đọc
   `tier_stock` gồm `presold`; seats đếm `seat_holds`). "Đã bán" của BTC = sức chứa − còn lại; doanh thu vẫn từ đơn `paid`.
10. **Trạng thái bán thống nhất** (quyết định của Claude, chưa có ai phản đối): suất đã bắt đầu thì đóng bán ở mọi nơi.
    Thêm phase `closed` ("Đang diễn"): mọi suất đã bắt đầu nhưng chưa qua ngày. `closed` không sửa/huỷ được.
    Tiền chỉ chuyển sang khả dụng ở `ended`. Trang sự kiện: suất đã bắt đầu bị vô hiệu, "Hết vé" xét mọi suất còn mở.
11. **Khán giả thấy hệ quả của thao tác BTC:** đơn bị hoàn (huỷ sự kiện) hiện "Sự kiện đã huỷ · đã hoàn tiền",
    ẩn QR, bỏ link tới trang sự kiện. Vé đã soát hiện giờ soát. "Vé của tôi" tải lại khi mở trang.
12. **Giới hạn mỗi đơn** chỉ khai báo ở `backend/app/config/rules.py`; chi tiết sự kiện trả `maxPerOrder`, giao diện đọc từ đó.

13. **Admin làm thật 4 mục** (chốt sau khi quét UI Admin), ngoài duyệt rút tiền:
    - **Xem trước hồ sơ trước khi duyệt** bằng chính component trang sự kiện / sơ đồ của khán giả; chặn duyệt hồ sơ
      có suất đã bắt đầu.
    - **Sổ đơn toàn sàn** (lọc / tìm / phân trang thật, dùng chung API và component với BTC) + **tra cứu mã vé** (chỉ xem).
    - **Gỡ / huỷ sự kiện vi phạm:** dùng chung logic huỷ + hoàn tiền với BTC, ghi `cancelled_by = 'admin'`;
      BTC và khách thấy "Sàn đã gỡ sự kiện" + lý do.
    - **Số liệu thật:** biểu đồ doanh thu, bục vinh danh, danh sách BTC (số sự kiện, doanh thu, phí, số dư, yêu cầu rút).
    Quyết định của Claude: bỏ "Hàng chờ ảo" và "Cấu hình hệ thống" khỏi menu (không có backend, ngoài phạm vi), xoá dữ liệu mẫu
    `frontend/src/constants/dashboards.js`; bỏ nút giả "Gửi lại vé qua email".
14. **Nhãn trạng thái dùng chung 3 bên** (`frontend/src/utils/status.js`): đơn `paid | refunded | cancelled`, phase sự kiện. Sửa lỗi
    Admin hiện đơn `refunded` thành "Đã trả" (đang dùng khoá `refund` / `unpaid` / `expired` không có trong CSDL).
15. **Số tổng của Admin khớp BTC:** vé / đơn chỉ đếm đơn `paid`; phí sàn = Σ `fee_of` theo từng sự kiện **của BTC**;
    doanh thu sự kiện do sàn tự bán (catalog, `organizer_id` NULL) tách riêng, không tính phí.

## Các hướng đã cân nhắc (brainstorming bù)
| Điểm | Đã chọn | Hướng khác & lý do không chọn |
|---|---|---|
| Hoàn tiền trong báo cáo | Trừ vào ngày mua | Trừ vào ngày hoàn (kiểu kế toán): phải sửa VIEW và biểu đồ Sổ cái, doanh thu một ngày có thể âm |
| Số dư âm | Chỉ rút tiền của sự kiện đã diễn | Cho âm rồi khoá rút tiền: phải xử lý "nợ sàn". Chặn huỷ khi thiếu tiền: BTC có thể bị kẹt không huỷ được |
| Suất diễn | 1 suất | Nhiều suất (tối đa 10): thêm khoảng 1 task, làm phần sửa sự kiện (D2) phức tạp, chưa cần cho đồ án |
| Sơ đồ cho BTC | Chọn sơ đồ có sẵn, chỉ đặt giá theo nhóm | Giữ BTC chỉ bán theo loại vé: gọn hơn nhưng hai giao diện không cân xứng |

## API (tiền tố `/api`, lỗi luôn là `{"error": "<câu tiếng Việt>"}`)
| Phương thức | Đường dẫn | Vai trò |
|---|---|---|
| GET | `/organizer/venue-maps` | organizer — sơ đồ có sẵn kèm nhóm giá + sức chứa |
| GET | `/organizer/orders` | organizer — lọc `q`, `eventId`, `status`, `from`, `to`, phân trang `page`, `pageSize` |
| GET | `/organizer/reports` | organizer — `from`, `to`, `eventId`, `groupBy=day|week|month` |
| POST | `/organizer/checkin` | organizer — `{code}` |
| PATCH | `/organizer/events/{id}` | organizer — form như POST, hạng vé kèm `id` nếu là hạng cũ |
| DELETE | `/organizer/events/{id}` | organizer — `{reason}` (bắt buộc khi đã có đơn) |
| GET / POST | `/organizer/withdrawals` | organizer — số dư + lịch sử / tạo yêu cầu |
| GET | `/admin/events/{id}` | admin — xem trước hồ sơ / sự kiện bất kỳ (kể cả chờ duyệt) |
| POST | `/admin/events/{id}/cancel` | admin — `{reason}` gỡ sự kiện vi phạm |
| GET | `/admin/orders` | admin — như `/organizer/orders`, thêm `organizerId` |
| GET | `/admin/tickets/{code}` | admin — tra cứu mã vé (chỉ xem) |
| GET | `/admin/reports` | admin — như `/organizer/reports`, toàn sàn, thêm `byOrganizer` |
| GET | `/admin/organizers` | admin — danh sách BTC kèm số liệu; `/admin/organizers/{id}/events` |
| GET | `/admin/withdrawals` | admin — `status` |
| POST | `/admin/withdrawals/{id}/decide` | admin — `{decision: paid|rejected, note}` |

Chi tiết hợp đồng JSON nằm trong kế hoạch `docs/plans/2026-11-07-organizer-dashboard-phase-2.md`.

## CSDL
- Migration 0006: `events.status` thêm `'cancelled'`; cột `cancel_reason text`, `cancelled_at timestamptz`;
  `orders.refunded_at timestamptz NULL`; `events.cancelled_by varchar(10) NULL CHECK IN ('organizer','admin')`.
- Migration 0007: bảng `withdrawals`.
- Soát vé dùng cột có sẵn `tickets.checked_in_at`; không thêm bảng.

## Ngoài phạm vi
BTC tự vẽ sơ đồ mới, trả vé về kho khi hoàn tiền (sự kiện đã huỷ thì không bán nữa nên không cần),
hoàn tiền thật qua cổng thanh toán, xuất CSV/PDF, đổi ngày diễn sự kiện đã duyệt, nhiều suất diễn cho sự kiện của BTC,
thông báo email, hoàn tiền từng đơn lẻ (chỉ hoàn hàng loạt khi huỷ sự kiện).
