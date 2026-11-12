-- Số dòng THẬT (count(*), không dùng ước lượng pg_class.reltuples) của mọi bảng nghiệp vụ.
-- Chạy: psql -h localhost -U ticketnhip -d ticketnhip_large -f backend/scripts/row_counts.sql
SELECT 'users' AS bang, count(*) AS so_dong FROM users
UNION ALL SELECT 'organizers', count(*) FROM organizers
UNION ALL SELECT 'categories', count(*) FROM categories
UNION ALL SELECT 'events', count(*) FROM events
UNION ALL SELECT 'shows', count(*) FROM shows
UNION ALL SELECT 'ticket_tiers', count(*) FROM ticket_tiers
UNION ALL SELECT 'tier_stock', count(*) FROM tier_stock
UNION ALL SELECT 'orders', count(*) FROM orders
UNION ALL SELECT 'order_items', count(*) FROM order_items
UNION ALL SELECT 'tickets', count(*) FROM tickets
UNION ALL SELECT 'seat_holds', count(*) FROM seat_holds
UNION ALL SELECT 'withdrawals', count(*) FROM withdrawals
UNION ALL SELECT 'coupons', count(*) FROM coupons
UNION ALL SELECT 'venue_maps', count(*) FROM venue_maps
UNION ALL SELECT 'map_seats', count(*) FROM map_seats
ORDER BY so_dong DESC;
