-- Tạo 2 CSDL phụ cho minh chứng học phần (chạy MỘT lần bằng tài khoản postgres):
--   ticketnhip_large   — bộ dữ liệu lớn (100 000 đơn) để đo hiệu năng (database/docs/du-lieu-lon.md, hieu-nang.md)
--   ticketnhip_restore — CSDL rỗng làm đích thử khôi phục bản sao lưu (database/docs/sao-luu-khoi-phuc.md)
-- psql -U postgres -h localhost -f database/create_extra_dbs.sql   (hoặc pgAdmin → Query Tool trên CSDL postgres)
CREATE DATABASE ticketnhip_large OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE ticketnhip_restore OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
