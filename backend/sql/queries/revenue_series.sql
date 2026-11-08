-- Q2 · Chuỗi doanh thu theo ngày / tuần / tháng: CTE generate_series lấp các mốc trống + LEFT JOIN + date_trunc giờ VN.
-- Mục đích : mỗi mốc thời gian một dòng (kể cả mốc không có đơn = 0) để vẽ biểu đồ liền mạch.
-- Đầu vào  : :unit ('day' | 'week' | 'month'), :d0 / :d1 (ngày đầu / cuối, giờ VN), :t0 / :t1 (cùng khoảng, timestamptz),
--            :org (NULL = toàn sàn), :event (NULL = mọi sự kiện).
-- Dùng ở   : GET /api/organizer/reports, GET /api/admin/reports → series[*] (org_reports.report).
-- Người phụ trách: (nhóm điền)
WITH buckets AS (
    SELECT generate_series(date_trunc(:unit, CAST(:d0 AS timestamp)), CAST(:d1 AS timestamp),
                           CAST('1 ' || :unit AS interval))::date AS bucket
),
agg AS (
    SELECT date_trunc(:unit, timezone('Asia/Ho_Chi_Minh', o.created_at))::date AS bucket,
           sum(o.total) AS revenue,
           count(*) AS orders,
           sum((SELECT count(*) FROM tickets t WHERE t.order_id = o.id)) AS tickets
    FROM orders o
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid'
      AND o.created_at >= :t0 AND o.created_at < :t1
      AND (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
    GROUP BY 1
)
SELECT b.bucket, coalesce(a.revenue, 0) AS revenue, coalesce(a.orders, 0) AS orders, coalesce(a.tickets, 0) AS tickets
FROM buckets b
LEFT JOIN agg a ON a.bucket = b.bucket
ORDER BY b.bucket
