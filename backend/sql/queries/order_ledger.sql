-- Q1 · Sổ đơn: JOIN 5 bảng (orders, events, organizers, shows, tickets) + lọc động + phân trang LIMIT/OFFSET + tổng.
-- Mục đích : danh sách đơn mới trước + tổng số đơn khớp bộ lọc + tóm tắt đơn đã thanh toán (trên TOÀN bộ kết quả lọc).
-- Đầu vào  : :org (BTC, NULL = toàn sàn), :event, :status ('all' | paid | refunded | cancelled), :t0 / :t1 (khoảng
--            created_at, NULL = không giới hạn), :pat ('%từ khoá%' đã escape, NULL = không tìm), :idpat ('từ khoá%'),
--            :limit, :offset.
-- Dùng ở   : GET /api/organizer/orders, GET /api/admin/orders (org_orders.list_orders).
-- Tìm kiếm : điều kiện trên biểu thức gộp (có chỉ mục GIN trigram ix_orders_buyer_trgm, migration 0008) để thu hẹp,
--            rồi điều kiện chính xác: mã đơn khớp tiền tố, tên / email / SĐT chứa từ khoá.
-- Người phụ trách: (nhóm điền)
WITH f AS (
    SELECT o.id, o.created_at, o.event_id, o.show_id, o.buyer_name, o.buyer_email, o.buyer_phone,
           o.subtotal, o.discount, o.total, o.method, o.status, o.kind, o.refunded_at,
           e.title AS event_title, org.org_name
    FROM orders o
    JOIN events e ON e.id = o.event_id
    LEFT JOIN organizers org ON org.user_id = e.organizer_id
    WHERE (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
      AND o.status NOT IN ('pending', 'expired')  -- giữ chỗ chưa thanh toán không vào sổ đơn
      AND (CAST(:status AS text) = 'all' OR o.status = :status)
      AND (CAST(:t0 AS timestamptz) IS NULL OR o.created_at >= :t0)
      AND (CAST(:t1 AS timestamptz) IS NULL OR o.created_at < :t1)
      AND (CAST(:pat AS text) IS NULL OR (
            lower(o.id || ' ' || o.buyer_name || ' ' || o.buyer_email || ' ' || o.buyer_phone) LIKE lower(:pat)
            AND (o.id ILIKE :idpat OR o.buyer_name ILIKE :pat OR o.buyer_email ILIKE :pat OR o.buyer_phone ILIKE :pat)))
),
s AS (
    SELECT count(*) AS total_count,
           count(*) FILTER (WHERE status = 'paid' AND kind = 'primary') AS paid_orders,
           coalesce(sum(total) FILTER (WHERE status = 'paid' AND kind = 'primary'), 0) AS paid_revenue,
           (SELECT count(*) FROM tickets t JOIN f p ON p.id = t.order_id
            WHERE p.status = 'paid' AND p.kind = 'primary') AS paid_tickets
    FROM f
),
page AS (
    SELECT * FROM f ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset
)
SELECT s.total_count, s.paid_orders, s.paid_revenue, s.paid_tickets,
       page.*, sh.starts_at, tc.tickets, tc.checked_in
FROM s
LEFT JOIN page ON true
LEFT JOIN shows sh ON sh.event_id = page.event_id AND sh.id = page.show_id
LEFT JOIN LATERAL (
    SELECT count(*) AS tickets, count(t.checked_in_at) AS checked_in FROM tickets t WHERE t.order_id = page.id
) tc ON true
ORDER BY page.created_at DESC, page.id DESC
