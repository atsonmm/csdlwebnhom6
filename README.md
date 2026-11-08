# TicketNhịp 🎟️

Nền tảng bán vé sự kiện **TicketNhịp**, phong cách "vé giấy in": nền be, viền mực đen, bóng đổ cứng.
Đồ án môn **CSDL Web**.

**Công nghệ:**
- Giao diện: React 19 · Vite · Tailwind CSS v4 · SwiperJS · lucide-react
- Máy chủ API: **Python FastAPI** · SQLAlchemy 2 (ORM) · Alembic
- Cơ sở dữ liệu: **PostgreSQL 18** (quản lý bằng pgAdmin 4)
- Kiểm thử: pytest (API) · Vitest + Testing Library (giao diện) · Postman

## Chạy dự án

Cần **Node.js 22.13+**, **Python 3.12+**, **PostgreSQL 18** và **Git**.

1. Cài máy chủ API + tạo CSDL + nạp dữ liệu: làm theo [`backend/README.md`](backend/README.md) (mục 1–3).
2. Chạy:

```bash
cd frontend
npm install      # lần đầu, hoặc khi package.json thay đổi
npm run dev      # chạy CÙNG LÚC giao diện (Vite, http://localhost:5173) + API FastAPI (cổng 8000)
```

Bản chạy thật (một máy chủ FastAPI phục vụ cả giao diện lẫn API, `ENV=prod`):
```bash
cd frontend
npm run build    # → frontend/dist
npm start        # http://localhost:8000 (FastAPI phục vụ luôn frontend/dist)
```

Kiểm thử:
```bash
cd frontend && npm test                             # giao diện (Vitest)
cd backend && .venv/Scripts/python.exe -m pytest    # API + CSDL (pytest, dùng CSDL ticketnhip_test)
```

Dữ liệu mẫu cho buổi trình bày (đơn hàng rải 7 ngày, có doanh thu cho dashboard):
`cd backend && .venv/Scripts/python.exe -m app.seed --demo`

## Máy chủ & dữ liệu

- **API:** `backend/` (FastAPI). Mọi đường dẫn bắt đầu bằng `/api`; tài liệu tự sinh ở http://localhost:8000/docs.
- **Cơ sở dữ liệu:** PostgreSQL — 19 bảng + 2 VIEW, có khoá ngoại / CHECK / chú thích tiếng Việt; lược đồ ở `database/schema.sql`, ERD xem bằng pgAdmin.
  Toàn bộ danh mục sự kiện (sự kiện, suất diễn, hạng vé, sơ đồ khu/ghế, trang chủ, mã giảm giá) nằm trong CSDL.
- **Tài khoản:** mật khẩu mã hoá bằng scrypt; phiên đăng nhập lưu bằng cookie `httpOnly` (30 ngày); sai mật khẩu 5 lần thì khoá 15 phút.
- **Đơn hàng:** máy chủ tự tính giá, kiểm tra mã giảm giá và trừ số vé còn lại trong **một transaction** — nhiều người mua cùng lúc
  không bao giờ bán vượt / bán trùng ghế (xem `backend/README.md` mục 10).
- **Quên mật khẩu:** chưa kết nối dịch vụ email nên liên kết đặt lại được ghi vào log máy chủ (và hiện trong modal khi `ENV=dev`).

Danh sách API đầy đủ: `backend/README.md` (mục 8–11) hoặc collection Postman `backend/postman/ticketnhip.postman_collection.json`.

**Chưa làm (cần tài khoản dịch vụ bên ngoài):** cổng thanh toán thật (VNPay/MoMo…), gửi email/SMS.

## 3 giao diện & phân quyền

| Vai trò | Vào bằng | Giao diện |
|---|---|---|
| Khách (`customer`) | Đăng ký trên trang chủ | Trang mua vé, “Vé của tôi” |
| Ban tổ chức (`organizer`) | Trang chủ → **Tạo sự kiện** → đăng ký Ban tổ chức | `/ban-to-chuc`: sổ cái, tạo sự kiện |
| Quản trị (`admin`) | Tài khoản tạo sẵn khi máy chủ khởi động | `/quan-tri`: duyệt sự kiện, sổ đơn |

**Tài khoản quản trị khi phát triển:** `admin@ticketnhip.vn` / `admin123456`.
Khi chạy thật, đặt biến môi trường `ADMIN_EMAIL` và `ADMIN_PASSWORD` trước lần chạy đầu (bản production không tạo mật khẩu mặc định).

Luồng: Ban tổ chức tạo sự kiện → **chờ duyệt** → Quản trị “Đóng dấu duyệt” → sự kiện lên mục **Mới lên sàn** ở trang chủ → khách mua → doanh thu và hoá đơn hiện trong sổ cái Ban tổ chức. Quyền được kiểm tra ở cả máy chủ (`requireRole`) lẫn giao diện.

## Bán vé: 3 kiểu & suất diễn

Mỗi sự kiện khai báo trong `src/data/eventDetails.js`:

| `layout` | Dùng cho | Sơ đồ (`map`) |
|---|---|---|
| `zones` | Concert, fanmeeting: chọn **khu vực** trên sơ đồ sân khấu | `arena`, `hall-grid`, `theatre-tiers` |
| `seats` | Nhà hát, nhạc kịch: chọn **từng ghế** | `nha-hat-lon`, `san-khau-nho` |
| `list` (mặc định) | Kịch, workshop: chỉ chọn **loại vé**, không sơ đồ | — |

- Sơ đồ nằm trong CSDL (bảng `venue_maps`, `map_groups`, `map_zones`, `map_seats`), giao diện lấy qua `GET /api/maps/{id}`.
- `shows: [{ date, time, endTime }]` khai báo nhiều suất diễn; số vé/ghế tính **riêng từng suất**.
- **Mỗi vé một mã check-in riêng** (vd. `K7QF-29XM`) lưu ở bảng `tickets`; vé chọn ghế ghi kèm số ghế.
- Ghế/khu "đã bán sẵn" là dữ liệu thật trong CSDL (`tier_stock.presold`, `seat_holds` không gắn đơn), nạp từ `backend/seed/catalog.json`.

## Cấu trúc thư mục

```
ticketnhip/
├─ backend/                        # API FastAPI — xem backend/README.md
│  ├─ app/
│  │  ├─ main.py                   # tạo ứng dụng, gắn middleware + router
│  │  ├─ config/                   # settings (biến môi trường), database (kết nối), rules (quy tắc cố định)
│  │  ├─ routers/                  # khai báo endpoint + quyền (mỏng)
│  │  ├─ controllers/              # xử lý request/response: đọc tham số, gọi service, commit/rollback
│  │  ├─ services/                 # nghiệp vụ: đặt vé, kho, sổ đơn, báo cáo, soát vé, huỷ/sửa sự kiện…
│  │  ├─ models/                   # bảng ORM (SQLAlchemy)
│  │  ├─ schemas/                  # Pydantic: body request + JSON trả ra
│  │  ├─ middlewares/              # auth (phiên/quyền), errors, ratelimit, request_guard (JSON-only)
│  │  ├─ utils/                    # băm mật khẩu, chuẩn hoá chữ, giờ VN, kiểm tra dữ liệu, phục vụ SPA
│  │  └─ seed.py                   # nạp dữ liệu mẫu: python -m app.seed [--demo]
│  ├─ alembic/                     # migration 0001…0006
│  ├─ tests/                       # pytest (API, CSDL, đồng thời, migration)
│  ├─ seed/                        # catalog.json (nguồn dữ liệu mẫu) + script xuất
│  ├─ postman/                     # bộ request Postman
│  ├─ scripts/                     # export_schema.sh, migrate_with_proof.py…
│  ├─ .env.example · requirements.txt
├─ frontend/                       # React + Vite
│  ├─ public/                      # favicon…
│  ├─ scripts/                     # dev-api.mjs (chạy FastAPI), capture-fixtures.mjs
│  ├─ src/
│  │  ├─ main.jsx · App.jsx        # điểm vào; App = router + provider
│  │  ├─ routes/AppRoutes.jsx      # toàn bộ đường dẫn
│  │  ├─ pages/<Trang>/            # Home, Event, Booking, MyTickets, Organizer, Admin, Policy, NotFound
│  │  │                            #   (component riêng của trang trong pages/<Trang>/components/)
│  │  ├─ components/
│  │  │  ├─ common/                # Button, Tabs, Toast, StatCard/Stamp/Panel/BarChart (widgets)…
│  │  │  ├─ layout/                # Layout, Header (+ header/*), Footer, DashboardShell, Access
│  │  │  └─ auth/ booking/ cards/ event/ sections/ legal/   # component theo nghiệp vụ, dùng ở nhiều trang
│  │  ├─ services/api.js           # gọi API (fetch + cookie phiên)
│  │  ├─ hooks/                    # useEvent, useOrgOrders, useOrgReport…
│  │  ├─ context/                  # AuthProvider, OrdersProvider
│  │  ├─ utils/                    # status, format, eventFormat, dashboard…
│  │  ├─ constants/                # nội dung tĩnh: menu, chính sách, giới hạn vé dự phòng…
│  │  ├─ styles/index.css          # design tokens Tailwind v4
│  │  ├─ assets/                   # hình ảnh, icon
│  │  └─ test/                     # thiết lập Vitest + fixture JSON chụp từ API
│  ├─ index.html · vite.config.js · package.json
├─ database/                       # schema.sql, create_db.sql, docs/ (minh chứng migration) — xem database/README.md
└─ docs/                           # FRONTEND_FEATURES_GUIDE.md, plans/, specs/, thông báo học phần
```

## Thành viên & phân công

| Người | Phụ trách | Nhánh |
|---|---|---|
| Người 1 (trưởng nhóm) | Nền móng: cấu hình, design tokens, UI dùng chung, Layout | `main` |
| Người 2 | Phần 1 Header đầy đủ · Phần 2 Hero slider | `feat/header-hero` |
| Người 3 | Phần 3 Sự kiện nổi bật · Phần 4 Ngôi sao & Poster · Phần 5 Chợ vé · Phần 6 Thẻ thành viên & Coupon | `feat/home-sections` |
| Người 4 | Hàng Nhạc sống/Sân khấu · Phần 7 Lịch diễn · Phần 8 Thành phố · Phần 9 Blog · Phần 10 Footer · Kết quả lọc | `feat/discover-footer` |

👉 Quy trình commit và quy ước làm việc: xem [CONTRIBUTING.md](CONTRIBUTING.md).
