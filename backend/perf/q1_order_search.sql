-- Q1 · Ô tìm của sổ đơn (Task A1/A3 — GET /api/organizer/orders?q=…, /api/admin/orders?q=…)
-- Tìm theo mã đơn / tên / email / SĐT, chuỗi con ở bất kỳ vị trí nào → LIKE '%…%' (B-tree không dùng được).
-- Biểu thức phải trùng khớp SEARCH_EXPR (org_orders.py, migration 0008) thì planner mới dùng chỉ mục trigram.
-- index: ix_orders_buyer_trgm
-- params: {"q": "0309772046"}
SELECT o.id, o.created_at, o.buyer_name, o.buyer_email, o.total, o.status, e.title
FROM orders o
JOIN events e ON e.id = o.event_id
WHERE lower(o.id || ' ' || o.buyer_name || ' ' || o.buyer_email || ' ' || o.buyer_phone) LIKE '%' || lower(:q) || '%'
ORDER BY o.created_at DESC, o.id DESC
LIMIT 20;
