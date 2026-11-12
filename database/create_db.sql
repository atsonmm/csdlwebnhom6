-- Tạo role và 2 CSDL cho TicketNhịp (chạy MỘT lần bằng tài khoản postgres)
-- psql -U postgres -h localhost -f backend/scripts/create_db.sql
CREATE ROLE ticketnhip LOGIN PASSWORD 'ticketnhip';
CREATE DATABASE ticketnhip OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE ticketnhip_test OWNER ticketnhip ENCODING 'UTF8' TEMPLATE template0;
