<!-- prettier-ignore -->
```text
csdlwebnhom6/
│
├── backend/                      ← Phần xử lý phía máy chủ
│   ├── src/
│   │   ├── config/               ← Cấu hình (kết nối database...)
│   │   │   └── db.js
│   │   ├── routes/               ← Khai báo đường dẫn API
│   │   │   ├── auth.routes.js
│   │   │   └── product.routes.js
│   │   ├── controllers/          ← Nhận yêu cầu, trả kết quả
│   │   │   ├── auth.controller.js
│   │   │   └── product.controller.js
│   │   ├── services/             ← Xử lý nghiệp vụ (tính toán, kiểm tra)
│   │   │   ├── auth.service.js
│   │   │   └── product.service.js
│   │   ├── models/               ← Làm việc trực tiếp với database (câu SQL)
│   │   │   ├── user.model.js
│   │   │   └── product.model.js
│   │   ├── middlewares/          ← "Trạm kiểm soát" chạy trước controller
│   │   │   └── auth.middleware.js
│   │   ├── utils/                ← Hàm tiện ích dùng chung
│   │   ├── app.js                ← Gắn các route, middleware vào ứng dụng
│   │   └── server.js             ← Điểm khởi động máy chủ
│   ├── .env.example
│   └── package.json
│
├── frontend/                     ← Phần giao diện người dùng thấy
│   ├── public/                   ← File tĩnh (favicon, ảnh không cần xử lý)
│   ├── src/
│   │   ├── assets/               ← Ảnh, icon, font dùng trong code
│   │   ├── components/           ← Các "mảnh" giao diện tái sử dụng
│   │   │   ├── common/           ← Button, Input, Modal, Loading...
│   │   │   └── layout/           ← Header, Footer, Sidebar
│   │   ├── pages/                ← Mỗi trang là một thư mục
│   │   │   ├── Home/
│   │   │   │   ├── Home.jsx
│   │   │   │   └── Home.css
│   │   │   ├── Login/
│   │   │   ├── Register/
│   │   │   └── NotFound/
│   │   ├── services/             ← Hàm gọi API sang backend
│   │   │   ├── api.js            ← Cấu hình chung (địa chỉ backend...)
│   │   │   ├── authService.js
│   │   │   └── productService.js
│   │   ├── hooks/                ← Hàm React tự viết, dùng lại nhiều nơi
│   │   ├── context/              ← Dữ liệu dùng chung toàn web (user đăng nhập, giỏ hàng)
│   │   ├── routes/               ← Khai báo đường dẫn các trang
│   │   │   └── AppRoutes.jsx
│   │   ├── utils/                ← Hàm tiện ích (định dạng tiền, ngày tháng...)
│   │   ├── styles/               ← CSS chung (màu sắc, font, reset)
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── database/                     ← Mọi thứ về cơ sở dữ liệu
│   ├── schema.sql                ← Lệnh tạo bảng
│   ├── seed.sql                  ← Dữ liệu mẫu để chạy thử
│   └── erd.png                   ← Sơ đồ quan hệ giữa các bảng
│
├── docs/                         ← Tài liệu dự án
│   └── api.md                    ← Danh sách API: đường dẫn, dữ liệu gửi/nhận
│
├── .gitignore
├── CONTRIBUTING.md
└── README.md
``` (Đảm bảo có 3 dấu backtick ở cuối để đóng khối mã lại)
