# Bản chụp dữ liệu JS cũ (trước khi chuyển sang PostgreSQL)

Các file này là dữ liệu sự kiện mà giao diện React từng nhúng thẳng trong `src/` (trước giai đoạn 6).
Giao diện **không còn dùng** chúng — mọi dữ liệu sự kiện giờ lấy từ API FastAPI / PostgreSQL.

Giữ lại để tái tạo được:
- `../catalog.json` (nguồn nạp danh mục): `TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs`
- `../../tests/fixtures/legacy_*.json` (dữ liệu đối chiếu trong test): `dump_legacy_events.mjs`, `dump_legacy_maps.mjs`

Muốn thêm / sửa sự kiện của sàn: sửa thẳng `catalog.json` rồi `python -m app.seed`, không cần sửa các file ở đây.
