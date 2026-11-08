-- Q3 · Doanh thu luỹ kế + so với kỳ trước: hàm cửa sổ SUM(...) OVER (ORDER BY mốc) và LAG.
-- Mục đích : với từng mốc (đã lấp mốc trống): tổng cộng dồn từ đầu khoảng, % thay đổi so với mốc liền trước
--            (NULL khi mốc trước bằng 0 — không chia cho 0).
-- Đầu vào  : giống Q2 (:unit, :d0, :d1, :t0, :t1, :org, :event).
-- Dùng ở   : series[*].cumulative, series[*].changePct của /organizer/reports, /admin/reports.
-- Người phụ trách: (nhóm điền)
WITH buckets AS (
    SELECT generate_series(date_trunc(:unit, CAST(:d0 AS timestamp)), CAST(:d1 AS timestamp),
                           CAST('1 ' || :unit AS interval))::date AS bucket
),
agg AS (
    SELECT date_trunc(:unit, timezone('Asia/Ho_Chi_Minh', o.created_at))::date AS bucket, sum(o.total) AS revenue
    FROM orders o
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid'
      AND o.created_at >= :t0 AND o.created_at < :t1
      AND (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
    GROUP BY 1
),
filled AS (
    SELECT b.bucket, coalesce(a.revenue, 0) AS revenue FROM buckets b LEFT JOIN agg a ON a.bucket = b.bucket
)
SELECT bucket,
       revenue,
       sum(revenue) OVER w AS cumulative,
       lag(revenue) OVER w AS previous,
       CASE WHEN lag(revenue) OVER w > 0
            THEN round(100.0 * (revenue - lag(revenue) OVER w) / lag(revenue) OVER w, 1) END AS change_pct
FROM filled
WINDOW w AS (ORDER BY bucket)
ORDER BY bucket
