# Sử dụng AI trong dự án TicketNhịp

Theo yêu cầu minh bạch của học phần CSDL Web. Công cụ: **Claude Code** (trợ lý lập trình AI của Anthropic, chạy trong terminal).

## Nguyên tắc nhóm đã áp dụng

- AI là **trợ lý**: đề xuất thiết kế, viết mã nháp, viết test, chạy lệnh kiểm tra. **Nhóm quyết định**:
  - phạm vi và thứ tự tính năng;
  - các quy tắc nghiệp vụ, ví dụ cách tính số dư rút tiền, mức sửa sự kiện sau khi duyệt, quy tắc huỷ / hoàn tiền;
  - việc chấp nhận hay sửa lại từng thay đổi.
- Mỗi tính năng có kế hoạch viết trước (`docs/plans/`, `docs/specs/`).
- Mỗi thay đổi đi kèm test tự động. Viết test trước, cho test thất bại, rồi mới cài đặt.
- Mọi quyết định AI tự đưa ra khi kế hoạch chưa nói rõ đều được ghi lại kèm lý do và lập luận, để nhóm đọc lại.
- **AI không commit mã.** Toàn bộ mã được thành viên nhóm đọc lại, chia nhánh, tạo Issue / PR và commit bằng tài khoản GitHub của chính mình.
- Mỗi thành viên phải **tự giải thích được** phần SQL mình phụ trách khi vấn đáp, không có AI hỗ trợ. Các file `backend/sql/queries/*.sql` có dòng "Người phụ trách" để nhóm điền.

## AI đã hỗ trợ những gì

| Hạng mục | Vai trò của AI | Nhóm kiểm soát / tự làm |
|---|---|---|
| **Thiết kế CSDL & migration** | Đề xuất lược đồ PostgreSQL và ràng buộc: CHECK, khoá ngoại nhiều cột, UNIQUE. Viết migration Alembic 0001–0008, gồm kiểm tra dữ liệu cũ và đếm dòng trước/sau khi chạy trên CSDL đã có dữ liệu | Chọn mô hình nghiệp vụ, duyệt từng ràng buộc, quyết định khi nào chạy migration trên CSDL dev |
| **Backend FastAPI** | Viết router / controller / service cho danh mục, tài khoản, đặt vé, Ban tổ chức, Admin, rút tiền, soát vé, sơ đồ khu / ghế | Quy tắc nghiệp vụ, nội dung thông báo lỗi tiếng Việt, đọc lại mã |
| **Giao dịch & đồng thời** | Cài đặt khoá dòng `FOR UPDATE` và `UPDATE` có điều kiện. Viết helper `tests/concurrency.py` để kiểm thử bằng **2 kết nối CSDL thật** và các test rollback (`database/docs/giao-dich-dong-thoi.md`) | Xác định các tình huống cạnh tranh cần chứng minh |
| **Truy vấn nâng cao** | Viết nháp 8 truy vấn SQL (CTE, hàm cửa sổ, EXISTS, FILTER, phân trang) và test đối chiếu với cách tính độc lập bằng Python (`database/docs/truy-van.md`) | Mỗi thành viên nhận phụ trách và giải thích truy vấn của mình |
| **Dữ liệu lớn & hiệu năng** | Script sinh 100 000 đơn (`app/seed_large.py`). Chọn 2 chỉ mục, viết công cụ đo `EXPLAIN (ANALYZE, BUFFERS)` trước/sau (`database/docs/du-lieu-lon.md`, `hieu-nang.md`) | Đánh giá kết quả đo và phần nhận xét |
| **Test** | Viết phần lớn bộ pytest (633 test) và Vitest (120 test), kể cả test giải mã QR bằng bộ đọc độc lập | Chạy lại test, bổ sung trường hợp |
| **Sao lưu / khôi phục** | Script `scripts/backup_restore.py` (pg_dump / pg_restore + đối chiếu số dòng). Chạy thử 2 lần và lập biên bản (`database/docs/sao-luu-khoi-phuc.md`) | Duyệt quy trình và chạy lại khi bảo vệ |
| **Triển khai** | Dockerfile, `docker-compose.yml` (3 dịch vụ: frontend, backend, CSDL), hướng dẫn tách 3 máy ảo (`docs/TRIEN_KHAI_DOCKER.md`) | Dựng máy ảo thật, cấu hình mạng / tường lửa |
| **Tài liệu** | ERD sinh tự động từ lược đồ (`database/docs/erd.png`), bảng API, `docs/FRONTEND_FEATURES_GUIDE.md` | Báo cáo cuối kỳ, slide |
| **Giao diện** | Bản khung (wireframe) ban đầu. Sửa `QrCode.jsx` để sinh mã QR thật, quét được ở cổng soát vé | **Nhóm tự viết giao diện chính thức** theo Figma và theo hợp đồng API trong guide |

## Lỗi / hạn chế của AI đã gặp và cách xử lý

- AI từng vẽ mã QR "minh hoạ" không quét được ở bản khung ban đầu. AI tự phát hiện khi rà soát luồng soát vé; sau đó đã thay bằng thư viện QR thật và thêm test giải mã.
- Dữ liệu sinh tự động lúc đầu quá đồng dạng (mọi email đều giống nhau), làm planner ước lượng sai khi chọn chỉ mục. Đã sửa bộ sinh để dữ liệu giống thật hơn, và chạy `VACUUM ANALYZE` trước khi đo.
- Thông tin AI đưa ra (phiên bản thư viện, số liệu, tên test) đều được kiểm lại bằng cách chạy lệnh thật; không chép số liệu khi chưa chạy.
