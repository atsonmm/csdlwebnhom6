-- Q8 · Số dư rút tiền của Ban tổ chức: CTE thực nhận theo từng sự kiện (phí sàn tính riêng từng sự kiện, làm tròn)
--      + SUM(...) FILTER cho phần đã quyết toán / tạm giữ và yêu cầu chờ / đã chuyển.
-- Mục đích : settled = thực nhận của sự kiện ĐÃ DIỄN (ngày VN của suất cuối < hôm nay); held = sự kiện đã duyệt chưa diễn;
--            pending / paid = tổng yêu cầu rút đang chờ / đã chuyển. available = settled − pending − paid (tính ở ứng dụng).
-- Đầu vào  : :orgs (mảng mã BTC, NULL = mọi BTC), :fee_rate (% phí sàn), :now.
-- Dùng ở   : withdrawals.balances → GET/POST /api/organizer/withdrawals, /api/admin/organizers, /api/admin/withdrawals.
-- Người phụ trách: (nhóm điền)
WITH per_event AS (
    SELECT e.organizer_id, e.id, e.status, sum(o.total) AS revenue,
           (SELECT max(s.starts_at) FROM shows s WHERE s.event_id = e.id) AS last_start
    FROM orders o
    JOIN events e ON e.id = o.event_id
    WHERE o.status = 'paid' AND o.kind = 'primary'
      AND e.organizer_id IS NOT NULL
      AND (CAST(:orgs AS integer[]) IS NULL OR e.organizer_id = ANY(CAST(:orgs AS integer[])))
    GROUP BY e.organizer_id, e.id, e.status
),
net AS (
    SELECT organizer_id, status,
           revenue - (revenue * :fee_rate + 50) / 100 AS net,
           (status = 'approved'
            AND timezone('Asia/Ho_Chi_Minh', last_start)::date
                < timezone('Asia/Ho_Chi_Minh', CAST(:now AS timestamptz))::date) AS ended
    FROM per_event
),
earned AS (
    SELECT organizer_id,
           coalesce(sum(net) FILTER (WHERE ended), 0) AS settled,
           coalesce(sum(net) FILTER (WHERE NOT ended AND status = 'approved'), 0) AS held
    FROM net
    GROUP BY organizer_id
),
taken AS (
    SELECT organizer_id,
           coalesce(sum(amount) FILTER (WHERE status = 'pending'), 0) AS pending,
           coalesce(sum(amount) FILTER (WHERE status = 'paid'), 0) AS paid
    FROM withdrawals
    WHERE CAST(:orgs AS integer[]) IS NULL OR organizer_id = ANY(CAST(:orgs AS integer[]))
    GROUP BY organizer_id
)
SELECT coalesce(e.organizer_id, t.organizer_id) AS organizer_id,
       coalesce(e.settled, 0) AS settled, coalesce(e.held, 0) AS held,
       coalesce(t.pending, 0) AS pending, coalesce(t.paid, 0) AS paid
FROM earned e
FULL JOIN taken t ON t.organizer_id = e.organizer_id
