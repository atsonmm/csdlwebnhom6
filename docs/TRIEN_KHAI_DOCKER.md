# Triển khai bằng Docker — 3 máy ảo (Frontend / Backend / CSDL + lưu trữ)

| Máy ảo | Dịch vụ compose | Image | Cổng | Ghi chú |
|---|---|---|---|---|
| **VM-DB** (CSDL + lưu trữ) | `db` | `postgres:18-alpine` | 5433 → 5432 | volume `db-data` (dữ liệu), thư mục `./.data/backups` (bản sao lưu) |
| **VM-BE** (Backend) | `backend` | build `backend/Dockerfile` (Python 3.14, FastAPI, uvicorn) | 8000 | khi khởi động: chờ CSDL → `alembic upgrade head` → nạp danh mục → uvicorn |
| **VM-FE** (Frontend) | `frontend` | build `frontend/Dockerfile` (Node 22 build → nginx 1.27) | 8080 → 80 | phục vụ React; `/api/*` chuyển sang `BACKEND_URL` (cùng nguồn → cookie phiên hoạt động) |

File liên quan: `docker-compose.yml`, `.env.example` (gốc), `backend/Dockerfile`, `backend/docker-entrypoint.sh`, `frontend/Dockerfile`, `frontend/nginx.conf.template`, `frontend/.env.example`.

## A. Chạy thử cả 3 dịch vụ trên một máy

```bash
cp .env.example .env          # rồi đổi POSTGRES_PASSWORD, ADMIN_PASSWORD
docker compose up -d --build
docker compose ps             # cả 3 "healthy"
# mở http://localhost:8080 — đăng nhập quản trị bằng ADMIN_EMAIL / ADMIN_PASSWORD trong .env
```

## B. Tách 3 máy ảo

Ví dụ IP: VM-DB `192.168.56.11`, VM-BE `192.168.56.12`, VM-FE `192.168.56.13`. Trên **mỗi** máy ảo:
1. Cài Docker Engine + Compose plugin.
2. Chép mã nguồn (hoặc `git clone`).
3. `cp .env.example .env`, sửa theo bảng dưới.

| Máy | Sửa trong `.env` | Lệnh chạy |
|---|---|---|
| VM-DB | `POSTGRES_PASSWORD`, `DB_PORT=5433` | `docker compose up -d db` |
| VM-BE | cùng `POSTGRES_*` như VM-DB; `DB_HOST=192.168.56.11`, `DB_HOST_PORT=5433`, `ADMIN_PASSWORD` | `docker compose up -d --build --no-deps backend` |
| VM-FE | `BACKEND_URL=http://192.168.56.12:8000` | `docker compose up -d --build --no-deps frontend` |

- `--no-deps`: chỉ chạy dịch vụ của máy đó. Compose không cố khởi động `db` hay `backend` trên máy hiện tại.
- Tường lửa:
  - VM-DB chỉ mở 5433 cho IP của VM-BE;
  - VM-BE chỉ mở 8000 cho IP của VM-FE;
  - người dùng chỉ truy cập VM-FE (cổng 8080, hoặc 80/443 qua reverse proxy).
- Mật khẩu CSDL dùng trong `DATABASE_URL`: nếu có ký tự đặc biệt (`@ : / ?`), phải mã hoá URL (vd. `@` → `%40`).
- Có HTTPS thì đặt `COOKIE_SECURE=true`. Chạy `http://IP` thì để `false`; nếu không, trình duyệt bỏ cookie phiên và mọi trang cần đăng nhập đều lỗi.

## C. Sao lưu / khôi phục trong Docker

Các lệnh chạy trên VM-DB. Bản sao lưu nằm ở `./.data/backups` của máy (volume `/backups` trong container).

```bash
# sao lưu
docker compose exec db sh -c 'pg_dump -Fc --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /backups/ticketnhip_$(date +%Y%m%d-%H%M).dump'
# khôi phục vào CSDL mới rồi đối chiếu số dòng (xem database/docs/sao-luu-khoi-phuc.md)
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" ticketnhip_restore && pg_restore --no-owner --exit-on-error -U "$POSTGRES_USER" -d ticketnhip_restore /backups/<tên>.dump'
```

Cách khác: chạy `backend/scripts/backup_restore.py` từ một máy có Python, trỏ `--database-url` tới `192.168.56.11:5433`. Script này tự đếm và so số dòng.

## D. Kiểm tra nhanh

```bash
curl http://<VM-BE>:8000/api/health          # {"ok": true, ...}
curl http://<VM-FE>:8080/api/categories       # qua nginx → backend
docker compose logs -f backend                # xem migration + seed khi khởi động
```

## E. Sự cố đã gặp khi chạy thử (2026-11-08, Windows + Docker Desktop, Compose v5.6)

- `docker compose up --build` dừng với thông báo `additional privileges requested: pass "--allow=fs.read=C:\Users\…\OneDrive"`.
  - Nguyên nhân: Compose v5 build bằng `bake`, mà thư mục dự án nằm trong OneDrive.
  - Cách xử lý: build từng image (tên trùng tên compose dùng), rồi chạy compose không kèm `--build`:
    ```bash
    docker build -t ticketnhip-backend ./backend
    docker build -t ticketnhip-frontend ./frontend
    docker compose up -d
    ```
  - Trên máy ảo Linux (dự án không nằm trong OneDrive), `docker compose up -d --build` chạy bình thường.
- Kết quả chạy thử:
  - cả 3 container *healthy*;
  - backend tự chạy migration 0001 → 0008 và nạp danh mục;
  - qua nginx `:8080`: `/api/health` → `{"ok":true,"postgres":"18.6"}`, trang React mở đúng (kể cả đường dẫn sâu như `/ban-to-chuc`);
  - đăng nhập: cookie `tn_session` có `HttpOnly` và `SameSite=lax`, không có `Secure` (`COOKIE_SECURE=false`), và được gửi lại ở các request sau;
  - đăng ký → đặt vé → "Vé của tôi" → Admin tra mã vé → đăng xuất đều đúng.
- `docker compose down` giữ lại volume `ticketnhip_db-data`. Muốn xoá sạch dữ liệu thì dùng `docker compose down -v`.
