-- Q6 · Khách mua nhiều nhất: tổng chi theo (Ban tổ chức, khách) + DENSE_RANK() OVER (PARTITION BY organizer_id ...).
-- Mục đích : top :top hạng khách của MỖI Ban tổ chức (DENSE_RANK: khách chi bằng nhau cùng hạng, không nhảy hạng).
-- Đầu vào  : :t0 / :t1, :org (NULL = mọi BTC, mỗi BTC một bảng xếp hạng riêng), :top.
-- Dùng ở   : GET /api/organizer/top-customers (org_reports.top_customers).
-- Người phụ trách: (nhóm điền)
WITH spent AS (
    SELECT e.organizer_id, o.user_id, count(*) AS orders, sum(o.total) AS spent,
           sum((SELECT count(*) FROM tickets t WHERE t.order_id = o.id)) AS tickets,
           max(o.created_at) AS last_order_at
    FROM orders o
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid'
      AND e.organizer_id IS NOT NULL
      AND o.created_at >= :t0 AND o.created_at < :t1
      AND (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
    GROUP BY e.organizer_id, o.user_id
),
ranked AS (
    SELECT spent.*, dense_rank() OVER (PARTITION BY organizer_id ORDER BY spent DESC) AS rank FROM spent
)
SELECT r.organizer_id, r.rank, u.id AS user_id, u.name, u.email, u.phone, r.orders, r.tickets, r.spent, r.last_order_at
FROM ranked r
JOIN users u ON u.id = r.user_id
WHERE r.rank <= :top
ORDER BY r.organizer_id, r.rank, r.last_order_at DESC, u.id
