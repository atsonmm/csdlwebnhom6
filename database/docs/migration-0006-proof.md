# Biên bản chạy migration 0006 trên CSDL dev (đã có dữ liệu)

Minh chứng học phần mục III.6. Mô tả thay đổi, kiểm tra dữ liệu cũ và phương án hạ phiên bản: [migration-0006.md](migration-0006.md).

- Thời điểm: 2026-11-08 09:57:25 +0700
- CSDL: `ticketnhip` · PostgreSQL 18.6 · Windows 11
- Lệnh: `cd backend && .venv/Scripts/python.exe -m alembic upgrade head` (sinh bởi script ghi biên bản, chạy 0.87 s)
- Phiên bản: `0006` → `0006`
- Kết luận: số dòng và phân bố trạng thái không đổi giữa hai lần đọc, **nhưng đây CHƯA phải biên bản trước/sau của lần nâng cấp**: CSDL dev đã ở `0006` trước khi script chạy (một phiên làm việc khác đã chạy `alembic upgrade head` 0005 → 0006 ngay trước 09:57 cùng ngày để chạy thử web — không ghi số dòng lúc đó), nên lệnh `upgrade head` không làm gì.
- Bằng chứng còn dùng được: cột mới tồn tại, cho phép NULL và toàn bộ dòng cũ đều NULL; 4 ràng buộc mới có mặt (bên dưới). Biên bản trước/sau đầy đủ: chạy lại bằng `downgrade 0005` → `upgrade head` có đếm dòng (an toàn vì chưa có sự kiện bị huỷ) — chờ người dùng đồng ý.

## Số dòng trước / sau

| Bảng | Trước | Sau |
|---|---:|---:|
| `users` | 7 | 7 |
| `organizers` | 1 | 1 |
| `events` | 42 | 42 |
| `shows` | 46 | 46 |
| `ticket_tiers` | 216 | 216 |
| `tier_stock` | 203 | 203 |
| `seat_holds` | 850 | 850 |
| `orders` | 38 | 38 |
| `order_items` | 38 | 38 |
| `tickets` | 72 | 72 |

## Trạng thái sự kiện / đơn trước → sau

| Bảng | Trạng thái | Trước | Sau |
|---|---|---:|---:|
| events | `approved` | 42 | 42 |
| orders | `paid` | 38 | 38 |

## Cột mới (đều cho phép NULL, dữ liệu cũ để NULL)

| Bảng | Cột | Kiểu | NULL |
|---|---|---|---|
| events | `cancel_reason` | text | YES |
| events | `cancelled_at` | timestamp with time zone | YES |
| events | `cancelled_by` | character varying | YES |
| orders | `refunded_at` | timestamp with time zone | YES |

Dòng cũ có giá trị ở cột mới: events = 0, orders = 0 (mong đợi 0, 0).

## Ràng buộc sau nâng cấp

- `ck_events_cancel_fields`: `CHECK ((((status)::text = 'cancelled'::text) = ((cancelled_at IS NOT NULL) AND (cancelled_by IS NOT NULL) AND (cancel_reason IS NOT NULL))))`
- `ck_events_cancelled_by`: `CHECK (((cancelled_by)::text = ANY ((ARRAY['organizer'::character varying, 'admin'::character varying])::text[])))`
- `ck_events_status`: `CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))`
- `ck_orders_refunded_at`: `CHECK (((refunded_at IS NULL) OR ((status)::text = 'refunded'::text)))`

## Đầu ra Alembic

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
