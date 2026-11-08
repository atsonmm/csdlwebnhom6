-- Q4 · Xếp hạng sự kiện theo doanh thu: CTE tổng theo sự kiện + RANK() và PERCENT_RANK() OVER (ORDER BY doanh thu DESC).
-- Mục đích : bảng "Theo sự kiện" của báo cáo + bục vinh danh; RANK để hai sự kiện bằng doanh thu cùng hạng (hạng sau nhảy).
-- Đầu vào  : :t0 / :t1, :org (NULL = toàn sàn), :event.
-- Dùng ở   : byEvent[*] (kèm rank, percentRank) của /organizer/reports, /admin/reports.
-- Người phụ trách: (nhóm điền)
WITH per_event AS (
    SELECT e.id AS event_id, e.title, e.organizer_id,
           sum(o.subtotal) AS gross, sum(o.discount) AS discount, sum(o.total) AS revenue, count(*) AS orders,
           sum((SELECT count(*) FROM tickets t WHERE t.order_id = o.id)) AS tickets
    FROM orders o
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid'
      AND o.created_at >= :t0 AND o.created_at < :t1
      AND (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
    GROUP BY e.id, e.title, e.organizer_id
)
SELECT per_event.*,
       rank() OVER (ORDER BY revenue DESC) AS rank,
       round(CAST(percent_rank() OVER (ORDER BY revenue DESC) AS numeric), 4) AS percent_rank
FROM per_event
ORDER BY revenue DESC, event_id
