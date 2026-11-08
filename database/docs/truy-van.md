# 8 truy vấn nghiệp vụ (học phần — mục III.3)

Mỗi truy vấn là một file trong `backend/sql/queries/`, chạy qua `app/services/sql_queries.py` bằng **tham số bind** (`:ten`, không ghép chuỗi). Đầu mỗi file ghi mục đích, đầu vào, API dùng và người phụ trách. Kiểm thử: `backend/tests/test_sql_queries.py` — mỗi truy vấn được so với một cách tính độc lập bằng Python.

Kết quả mẫu: chạy chỉ-đọc trên CSDL demo `ticketnhip` ngày 2026-11-08 (khoảng 30 ngày 2026-10-10 → 2026-11-08; tối đa 5 dòng).

| # | File | Kỹ thuật | API / màn hình | Người phụ trách |
|---|---|---|---|---|
| Q1 | `order_ledger.sql` | JOIN 5 bảng, lọc động, phân trang LIMIT/OFFSET, đếm tổng | GET /api/organizer/orders, /api/admin/orders | |
| Q2 | `revenue_series.sql` | CTE generate_series lấp mốc trống, LEFT JOIN, date_trunc giờ VN | series của /organizer/reports, /admin/reports | |
| Q3 | `revenue_running.sql` | SUM() OVER, LAG() | series[*].cumulative, changePct | |
| Q4 | `event_ranking.sql` | CTE + RANK(), PERCENT_RANK() | byEvent[*].rank / percentRank | |
| Q5 | `tier_sell_through.sql` | CTE + EXISTS + SUM() OVER (PARTITION BY) | byTier[*].revenueShare (+ fillRate) | |
| Q6 | `top_customers.sql` | DENSE_RANK() OVER (PARTITION BY organizer_id) | GET /api/organizer/top-customers | |
| Q7 | `events_without_sales.sql` | NOT EXISTS + truy vấn con tương quan | GET /api/admin/events/stale | |
| Q8 | `withdrawal_balance.sql` | CTE + SUM() FILTER (WHERE …) + FULL JOIN | GET/POST /api/organizer/withdrawals, /api/admin/organizers | |

## Q1 · Sổ đơn — JOIN 5 bảng, lọc động, phân trang LIMIT/OFFSET, đếm tổng

```sql
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
           o.subtotal, o.discount, o.total, o.method, o.status, o.refunded_at,
           e.title AS event_title, org.org_name
    FROM orders o
    JOIN events e ON e.id = o.event_id
    LEFT JOIN organizers org ON org.user_id = e.organizer_id
    WHERE (CAST(:org AS integer) IS NULL OR e.organizer_id = :org)
      AND (CAST(:event AS integer) IS NULL OR o.event_id = :event)
      AND (CAST(:status AS text) = 'all' OR o.status = :status)
      AND (CAST(:t0 AS timestamptz) IS NULL OR o.created_at >= :t0)
      AND (CAST(:t1 AS timestamptz) IS NULL OR o.created_at < :t1)
      AND (CAST(:pat AS text) IS NULL OR (
            lower(o.id || ' ' || o.buyer_name || ' ' || o.buyer_email || ' ' || o.buyer_phone) LIKE lower(:pat)
            AND (o.id ILIKE :idpat OR o.buyer_name ILIKE :pat OR o.buyer_email ILIKE :pat OR o.buyer_phone ILIKE :pat)))
),
s AS (
    SELECT count(*) AS total_count,
           count(*) FILTER (WHERE status = 'paid') AS paid_orders,
           coalesce(sum(total) FILTER (WHERE status = 'paid'), 0) AS paid_revenue,
           (SELECT count(*) FROM tickets t JOIN f p ON p.id = t.order_id WHERE p.status = 'paid') AS paid_tickets
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
```

Tham số mẫu: `org=NULL, event=NULL, status=all, t0=NULL, t1=NULL, pat=NULL, idpat=NULL, limit=5, offset=0`

| total_count | id | created_at | event_title | buyer_name | total | status | tickets |
|---|---|---|---|---|---|---|---|
| 38 | TNZ895U4JZ | 2026-11-07 02:19 | Săn Mây Cầu Đất | Trần Quốc Bảo | 1050000 | paid | 3 |
| 38 | TNW6ZLL9QE | 2026-11-07 02:19 | Liveshow Phố Biển | Nguyễn Minh Anh | 700000 | paid | 1 |
| 38 | TNVP4N6PQ7 | 2026-11-07 02:19 | Futsal Cup Sài Gòn | Trần Quốc Bảo | 670000 | paid | 2 |
| 38 | TN39LWV8CN | 2026-11-07 02:19 | Kịch: Hẹn Anh Ở Bến Sông | Trần Quốc Bảo | 720000 | paid | 2 |
| 38 | TNG73X2CZY | 2026-11-06 22:22 | Birthday Show: Bạch Khanh | Võ Ngọc Lan | 7500000 | paid | 3 |

## Q2 · Chuỗi doanh thu — CTE generate_series lấp mốc trống, LEFT JOIN, date_trunc giờ VN

```sql
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
```

Tham số mẫu: `unit=week, d0=2026-10-10, d1=2026-11-08, org=NULL, event=NULL, t0=2026-10-10 00:00, t1=2026-11-09 00:00`

| bucket | revenue | orders | tickets |
|---|---|---|---|
| 2026-10-05 | 0 | 0 | 0 |
| 2026-10-12 | 0 | 0 | 0 |
| 2026-10-19 | 0 | 0 | 0 |
| 2026-10-26 | 4389000 | 4 | 5 |
| 2026-11-02 | 69575000 | 34 | 67 |

## Q3 · Doanh thu luỹ kế + so với kỳ trước — SUM() OVER, LAG()

```sql
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
```

Tham số mẫu: `unit=week, d0=2026-10-10, d1=2026-11-08, org=NULL, event=NULL, t0=2026-10-10 00:00, t1=2026-11-09 00:00`

| bucket | revenue | cumulative | previous | change_pct |
|---|---|---|---|---|
| 2026-10-05 | 0 | 0 |  |  |
| 2026-10-12 | 0 | 0 | 0 |  |
| 2026-10-19 | 0 | 0 | 0 |  |
| 2026-10-26 | 4389000 | 4389000 | 0 |  |
| 2026-11-02 | 69575000 | 73964000 | 4389000 | 1485.2 |

## Q4 · Xếp hạng sự kiện — CTE + RANK(), PERCENT_RANK()

```sql
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
```

Tham số mẫu: `org=NULL, event=NULL, t0=2026-10-10 00:00, t1=2026-11-09 00:00`

| event_id | title | revenue | orders | tickets | rank | percent_rank |
|---|---|---|---|---|---|---|
| 5 | Birthday Show: Bạch Khanh | 9200000 | 2 | 5 | 1 | 0.0000 |
| 4 | Live Concert XV — 15 năm | 7150000 | 2 | 3 | 2 | 0.0455 |
| 14 | Live Show: Ba Giọng Ca | 7150000 | 2 | 5 | 2 | 0.0455 |
| 3 | Fanmeeting “Về Nhà” | 5445000 | 2 | 5 | 4 | 0.1364 |
| 38 | Gánh Hát Rong | 5290000 | 2 | 3 | 5 | 0.1818 |

## Q5 · Bán theo hạng vé — CTE + EXISTS + SUM() OVER (PARTITION BY)

```sql
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
```

Tham số mẫu: `org=NULL, event=NULL, t0=2026-10-10 00:00, t1=2026-11-09 00:00`

| event_title | tier_name | price | sold | revenue | revenue_share |
|---|---|---|---|---|---|
| Concert Đêm 4: Hẹn Giữa Tinh Hà | CAT 2A | 1800000 | 2 | 3600000 | 100.0 |
| Concert Anh Em Vượt Núi | FANZONE B | 2200000 | 1 | 2200000 | 100.0 |
| Fanmeeting “Về Nhà” | Tổ 3 · Trái | 1099000 | 2 | 2198000 | 40.0 |
| Fanmeeting “Về Nhà” | Tổ 3 · Phải | 1099000 | 3 | 3297000 | 60.0 |
| Live Concert XV — 15 năm | VIP-2 | 3000000 | 2 | 6000000 | 83.3 |

## Q6 · Khách mua nhiều nhất — DENSE_RANK() OVER (PARTITION BY organizer_id)

```sql
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
```

Tham số mẫu: `org=NULL, top=3, t0=2026-10-10 00:00, t1=2026-11-09 00:00`

*(không có dòng nào trên bộ demo)*

## Q7 · Sự kiện đang bán chưa có đơn — NOT EXISTS + truy vấn con tương quan

```sql
-- Q7 · Sự kiện đang bán nhưng "đứng": NOT EXISTS đơn đã thanh toán trong :days ngày + truy vấn con tương quan lần bán gần nhất.
-- Mục đích : nhắc Admin những sự kiện đang mở bán (đã duyệt, đã tới giờ mở bán, suất cuối chưa bắt đầu) mà không bán
--            được vé nào trong :days ngày qua — có thể cần hỗ trợ quảng bá hoặc kiểm tra.
-- Đầu vào  : :days, :now (thời điểm hiện tại — truyền từ ứng dụng để khớp quy tắc phase).
-- Dùng ở   : GET /api/admin/events/stale?days=7 (manage.stale_events).
-- Người phụ trách: (nhóm điền)
SELECT e.id, e.slug, e.title, e.organizer_id, org.org_name,
       coalesce(e.sale_start, e.reviewed_at) AS sale_opens_at,
       sh.last_start,
       (SELECT max(o.created_at) FROM orders o WHERE o.event_id = e.id AND o.status = 'paid') AS last_sale_at
FROM events e
JOIN LATERAL (SELECT max(s.starts_at) AS last_start FROM shows s WHERE s.event_id = e.id AND s.active) sh ON true
LEFT JOIN organizers org ON org.user_id = e.organizer_id
WHERE e.status = 'approved'
  AND e.active
  AND (coalesce(e.sale_start, e.reviewed_at) IS NULL OR coalesce(e.sale_start, e.reviewed_at) <= :now)
  AND sh.last_start > :now
  AND NOT EXISTS (
      SELECT 1 FROM orders o
      WHERE o.event_id = e.id AND o.status = 'paid'
        AND o.created_at >= CAST(:now AS timestamptz) - make_interval(days => :days)
  )
ORDER BY last_sale_at NULLS FIRST, sh.last_start, e.id
```

Tham số mẫu: `days=7, now=2026-11-08 16:54`

| id | title | org_name | sale_opens_at | last_sale_at |
|---|---|---|---|---|
| 25 | Hội chợ Đồ Cũ Cuối Tuần |  |  |  |
| 11 | Kịch: Tấm Cám Đại Chiến |  |  |  |
| 7 | Khi Di sản hoá Vũ điệu |  |  |  |
| 10 | Vở diễn: Xóm Trọ Lắm Trò |  |  |  |
| 27 | Đêm Đờn Ca Tài Tử |  |  |  |

## Q8 · Số dư rút tiền — CTE + SUM() FILTER (WHERE …) + FULL JOIN

```sql
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
    WHERE o.status = 'paid'
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
```

Tham số mẫu: `orgs=NULL, fee_rate=5, now=2026-11-08 16:54`

*Chưa chạy được trên CSDL demo: ProgrammingError — CSDL dev chưa nâng lên migration 0007 (bảng withdrawals).*
