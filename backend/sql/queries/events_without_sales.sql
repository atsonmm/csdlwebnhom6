-- Q7 · Sự kiện đang bán nhưng "đứng": NOT EXISTS đơn đã thanh toán trong :days ngày + truy vấn con tương quan lần bán gần nhất.
-- Mục đích : nhắc Admin những sự kiện đang mở bán (đã duyệt, đã tới giờ mở bán, suất cuối chưa bắt đầu) mà không bán
--            được vé nào trong :days ngày qua — có thể cần hỗ trợ quảng bá hoặc kiểm tra.
-- Đầu vào  : :days, :now (thời điểm hiện tại — truyền từ ứng dụng để khớp quy tắc phase).
-- Dùng ở   : GET /api/admin/events/stale?days=7 (manage.stale_events).
-- Người phụ trách: (nhóm điền)
SELECT e.id, e.slug, e.title, e.organizer_id, org.org_name,
       coalesce(e.sale_start, e.reviewed_at) AS sale_opens_at,
       sh.last_start,
       (SELECT max(o.created_at) FROM orders o WHERE o.event_id = e.id AND o.status = 'paid' AND o.kind = 'primary') AS last_sale_at
FROM events e
JOIN LATERAL (SELECT max(s.starts_at) AS last_start FROM shows s WHERE s.event_id = e.id AND s.active) sh ON true
LEFT JOIN organizers org ON org.user_id = e.organizer_id
WHERE e.status = 'approved'
  AND e.active
  AND (coalesce(e.sale_start, e.reviewed_at) IS NULL OR coalesce(e.sale_start, e.reviewed_at) <= :now)
  AND sh.last_start > :now
  AND NOT EXISTS (
      SELECT 1 FROM orders o
      WHERE o.event_id = e.id AND o.status = 'paid' AND o.kind = 'primary'
        AND o.created_at >= CAST(:now AS timestamptz) - make_interval(days => :days)
  )
ORDER BY last_sale_at NULLS FIRST, sh.last_start, e.id
