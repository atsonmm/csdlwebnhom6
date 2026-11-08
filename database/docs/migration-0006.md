# Migration 0006 — Huỷ sự kiện & thời điểm hoàn tiền

Minh chứng cho yêu cầu học phần (mục III.6): *thay đổi schema có quản lý phiên bản trên CSDL đã có dữ liệu, kèm kiểm tra dữ liệu cũ và phương án xử lý khi lỗi*.

Tệp: `backend/alembic/versions/0006_event_cancel.py` (Alembic, `down_revision = 0005`).

## Thay đổi

| Bảng | Thay đổi | Lý do |
|---|---|---|
| `events` | `ck_events_status` thêm `'cancelled'` | Sự kiện đã có đơn không xoá được (đơn tham chiếu suất), nên huỷ mềm |
| `events` | thêm `cancel_reason text`, `cancelled_at timestamptz`, `cancelled_by varchar(10)` (đều cho phép NULL) | Khách thấy lý do; Admin/BTC biết ai huỷ, lúc nào |
| `events` | `ck_events_cancelled_by`: `cancelled_by IN ('organizer','admin')` | Chỉ hai bên được huỷ |
| `events` | `ck_events_cancel_fields`: `(status = 'cancelled') = (cancelled_at, cancelled_by, cancel_reason đều NOT NULL)` | Không có sự kiện "huỷ nửa vời" |
| `orders` | thêm `refunded_at timestamptz` (NULL) | Hiện ngày hoàn trong sổ đơn / vé của khách |
| `orders` | `ck_orders_refunded_at`: `refunded_at IS NULL OR status = 'refunded'` | Đơn chưa hoàn thì không có ngày hoàn; đơn hoàn **trước** 0006 giữ NULL |

## Kiểm tra dữ liệu cũ (trong chính migration)

1. Trước khi đổi: đếm sự kiện có trạng thái ngoài `pending/approved/rejected` → khác 0 thì **dừng** (không sửa âm thầm).
2. Đếm số dòng `events`, `orders` trước và sau → khác nhau thì **dừng** (transaction của Alembic rollback toàn bộ).
3. Chỉ thêm cột cho phép NULL và nới ràng buộc → không viết lại dòng cũ, không khoá bảng lâu.

## Hạ phiên bản (phương án khi lỗi)

- `alembic downgrade 0005` khi **chưa** có sự kiện `cancelled` → xoá các cột/ràng buộc mới, trả `ck_events_status` về như cũ.
- Khi **đã** có sự kiện `cancelled` → downgrade dừng với thông báo, không xoá dữ liệu. Xử lý tay trước khi hạ: đổi các sự kiện đó về `approved` + `active = false` (ngừng bán, giữ đơn) rồi hạ lại.
- Mọi bước chạy trong một transaction (PostgreSQL hỗ trợ DDL trong transaction) → lỗi giữa chừng không để lược đồ dở dang.

## Kiểm thử tự động

`backend/tests/test_migrations.py::test_0006_upgrade_on_populated_db` — chạy trong schema riêng `mig0006` của CSDL test:

1. `upgrade 0005` → nạp toàn bộ catalog + 1 khách + 2 đơn (1 `paid`, 1 `refunded`) bằng SQL thuần.
2. `upgrade 0006` → số dòng 8 bảng (`events, shows, ticket_tiers, tier_stock, orders, order_items, tickets, users`) không đổi; phân bố trạng thái sự kiện không đổi; mọi cột mới là NULL; đặt `status='cancelled'` thiếu lý do bị `ck_events_cancel_fields` chặn.
3. `downgrade 0005` khi chưa có sự kiện huỷ → thành công; nâng lại 0006.
4. Huỷ một sự kiện đúng quy tắc → `downgrade 0005` bị chặn, dữ liệu còn nguyên, `alembic_version` vẫn `0006`.

Lệnh: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_migrations.py -v`

## Chạy trên CSDL dev (`ticketnhip`, đã có dữ liệu demo)

> Chưa chạy — chờ người dùng đồng ý (plan: không tự `alembic upgrade` trên CSDL dev). Khi chạy, ghi lại bảng dưới.

```sql
-- trước và sau khi nâng cấp
SELECT 'events' AS bang, count(*) FROM events UNION ALL SELECT 'orders', count(*) FROM orders
UNION ALL SELECT 'tickets', count(*) FROM tickets;
SELECT status, count(*) FROM events GROUP BY status ORDER BY 1;
```

| Bảng | Trước (0005) | Sau (0006) |
|---|---|---|
| events | | |
| orders | | |
| tickets | | |
