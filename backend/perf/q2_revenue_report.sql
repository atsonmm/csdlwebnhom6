-- Q2 · Báo cáo doanh thu toàn sàn theo ngày (Task B3 — GET /api/admin/reports?groupBy=day, khoảng 7 ngày gần nhất)
-- Chỉ đơn 'paid' trong một khoảng thời gian → chỉ mục (status, created_at) INCLUDE (event_id, total) cho phép
-- quét đúng khoảng và đọc tổng tiền ngay trên chỉ mục (Index Only Scan) thay vì quét cả bảng orders.
-- index: ix_orders_status_created
-- params: {"days": 7}
SELECT date_trunc('day', timezone('Asia/Ho_Chi_Minh', o.created_at)) AS ngay,
       count(*) AS so_don,
       sum(o.total) AS doanh_thu
FROM orders o
WHERE o.status = 'paid'
  AND o.created_at >= now() - make_interval(days => :days)
  AND o.created_at < now()
GROUP BY 1
ORDER BY 1;
