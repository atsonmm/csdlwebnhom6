-- Q5 · Bán theo hạng vé: CTE số đã bán trong khoảng + JOIN hạng vé + tỉ trọng doanh thu trong sự kiện (SUM OVER PARTITION).
-- Mục đích : mỗi hạng vé có bán trong khoảng (lọc một sự kiện → đủ mọi hạng đang mở của sự kiện đó, kể cả hạng chưa bán)
--            với số vé, doanh thu và % doanh thu của hạng trong sự kiện. Sức chứa / tỉ lệ lấp đầy lấy từ kho chung
--            stock.tier_stats (một nguồn số liệu kho cho cả khán giả, BTC, Admin).
-- Đầu vào  : :t0 / :t1, :org, :event.
-- Dùng ở   : byTier[*] của /organizer/reports, /admin/reports.
-- Người phụ trách: (nhóm điền)
WITH sold AS (
    SELECT i.event_id, i.tier_id, sum(i.qty) AS qty, sum(i.qty * i.price) AS revenue
    FROM order_items i
    JOIN orders o ON o.id = i.order_id
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid'
      AND o.created_at >= :t0 AND o.created_at < :t1
      AND (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
    GROUP BY i.event_id, i.tier_id
),
tiers AS (
    SELECT t.event_id, e.title AS event_title, t.id AS tier_id, t.name AS tier_name, t.price, t.sort_order
    FROM ticket_tiers t
    JOIN events e ON e.id = t.event_id
    WHERE (CAST(:event AS integer) IS NOT NULL AND t.event_id = :event AND t.active)
       OR (CAST(:event AS integer) IS NULL
           AND EXISTS (SELECT 1 FROM sold s WHERE s.event_id = t.event_id AND s.tier_id = t.id))
)
SELECT tiers.*, coalesce(s.qty, 0) AS sold, coalesce(s.revenue, 0) AS revenue,
       round(100.0 * coalesce(s.revenue, 0)
             / nullif(sum(coalesce(s.revenue, 0)) OVER (PARTITION BY tiers.event_id), 0), 1) AS revenue_share
FROM tiers
LEFT JOIN sold s ON s.event_id = tiers.event_id AND s.tier_id = tiers.tier_id
ORDER BY tiers.event_id, tiers.sort_order, tiers.tier_id
