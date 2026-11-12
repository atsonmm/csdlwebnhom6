"""Sinh bộ dữ liệu LỚN để đo hiệu năng (học phần: ≥ 3 bảng ≥ 10 000 dòng, 1 bảng ≥ 100 000 dòng).

    python -m app.seed_large --scale 1.0 [--seed 42] [--database-url postgresql+psycopg://…/ticketnhip_large]

Mô phỏng 12 tháng hoạt động của sàn (scale = 1.0):
    users (khách) ≥ 12 000 · ~60 Ban tổ chức · ≥ 400 sự kiện (đủ phase) · orders 100 000 · order_items ≥ 120 000 ·
    tickets ≥ 200 000 · withdrawals ~1 000.
Mọi dòng đi qua đúng ràng buộc CSDL (FK, CHECK, UNIQUE) và quy tắc nghiệp vụ: mua sau khi duyệt / mở bán và trước giờ
diễn, sự kiện huỷ thì mọi đơn đã hoàn, kho tier_stock.sold = số vé đã bán (đơn paid + refunded — vé không về kho),
~70 % vé của sự kiện đã diễn đã soát, yêu cầu rút tiền không vượt thực nhận của sự kiện đã diễn.

Sinh bằng SQL theo lô (INSERT … SELECT … FROM generate_series) trong MỘT transaction, setseed() để chạy lại ra cùng
dữ liệu. Chạy lại an toàn: xoá trước dữ liệu do chính script tạo (email @lon.ticketnhip.vn, mã đơn tiền tố TL,
slug tiền tố lon-), không chạm catalog / dữ liệu demo. Cần catalog (thể loại) đã nạp: python -m app.seed.
"""
import argparse
import random
import time
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import Base, make_engine
from app.config.settings import settings
from app.utils.security import hash_password

EMAIL_DOMAIN = "@lon.ticketnhip.vn"
SLUG_PREFIX = "lon-"
ORDER_PREFIX = "TL"
PASSWORD = "lon123456"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # như mã vé thật; mã sinh ra có thêm "0" nên không trùng mã thật

CITIES = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Huế", "Đà Lạt", "Hải Phòng", "Cần Thơ", "Nha Trang"]
VENUES = ["Nhà hát Lớn", "Cung Văn hoá", "Sân vận động", "Trung tâm Hội nghị", "Nhà văn hoá Thanh niên", "Sân khấu ngoài trời"]
HO = [("Nguyễn", "nguyen"), ("Trần", "tran"), ("Lê", "le"), ("Phạm", "pham"), ("Hoàng", "hoang"), ("Huỳnh", "huynh"),
      ("Phan", "phan"), ("Vũ", "vu"), ("Võ", "vo"), ("Đặng", "dang"), ("Bùi", "bui"), ("Đỗ", "do"), ("Hồ", "ho"),
      ("Ngô", "ngo"), ("Dương", "duong"), ("Lý", "ly")]
DEM = ["Văn", "Thị", "Minh", "Ngọc", "Thanh", "Hữu", "Đức", "Quang", "Thu", "Hoài", "Gia", "Khánh"]
TEN = [("An", "an"), ("Bình", "binh"), ("Châu", "chau"), ("Dũng", "dung"), ("Giang", "giang"), ("Hà", "ha"),
       ("Hải", "hai"), ("Hạnh", "hanh"), ("Hùng", "hung"), ("Khoa", "khoa"), ("Lan", "lan"), ("Linh", "linh"),
       ("Long", "long"), ("Mai", "mai"), ("Nam", "nam"), ("Nga", "nga"), ("Phúc", "phuc"), ("Quân", "quan"),
       ("Sơn", "son"), ("Tâm", "tam"), ("Thảo", "thao"), ("Trang", "trang"), ("Tuấn", "tuan"), ("Vy", "vy"),
       ("Yến", "yen"), ("Huy", "huy"), ("Phương", "phuong")]
MAILS = ["@gmail.com", "@yahoo.com", "@outlook.com", "@icloud.com", "@hotmail.com"]
TOPICS = ["Đêm nhạc", "Liveshow", "Hoà nhạc", "Kịch", "Hài độc thoại", "Lễ hội", "Workshop", "Triển lãm"]


def _counts_by_marker(db: Session) -> dict[str, int]:
    m = {"d": f"%{EMAIL_DOMAIN}", "s": f"{SLUG_PREFIX}%", "o": f"{ORDER_PREFIX}%"}
    sql = {
        "users": "SELECT count(*) FROM users WHERE email LIKE :d",
        "organizers": "SELECT count(*) FROM organizers o JOIN users u ON u.id = o.user_id WHERE u.email LIKE :d",
        "events": "SELECT count(*) FROM events WHERE slug LIKE :s",
        "shows": "SELECT count(*) FROM shows s JOIN events e ON e.id = s.event_id WHERE e.slug LIKE :s",
        "ticket_tiers": "SELECT count(*) FROM ticket_tiers t JOIN events e ON e.id = t.event_id WHERE e.slug LIKE :s",
        "tier_stock": "SELECT count(*) FROM tier_stock t JOIN events e ON e.id = t.event_id WHERE e.slug LIKE :s",
        "orders": "SELECT count(*) FROM orders WHERE id LIKE :o",
        "order_items": "SELECT count(*) FROM order_items WHERE order_id LIKE :o",
        "tickets": "SELECT count(*) FROM tickets WHERE order_id LIKE :o",
        "withdrawals": "SELECT count(*) FROM withdrawals w JOIN users u ON u.id = w.organizer_id WHERE u.email LIKE :d",
    }
    return {k: int(db.execute(text(v), m).scalar()) for k, v in sql.items()}


def row_counts(db: Session) -> dict[str, int]:
    """Số dòng THẬT (count(*)) của mọi bảng"""
    return {t.name: int(db.execute(text(f"SELECT count(*) FROM {t.name}")).scalar()) for t in Base.metadata.sorted_tables}


def clear(db: Session) -> None:
    """Xoá dữ liệu do script này tạo (đơn trước vì FK đơn → suất không cascade), giữ nguyên mọi thứ khác"""
    db.execute(text("DELETE FROM orders WHERE id LIKE :o"), {"o": f"{ORDER_PREFIX}%"})
    db.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%{EMAIL_DOMAIN}"})  # cascade: BTC → sự kiện → …


def _code_sql(col: str) -> str:
    """Mã vé 'L0XX-XXXX' từ số thứ tự: hoán vị (nhân số lẻ mod 2^30) rồi đổi sang cơ số 32 — duy nhất, khớp CODE_RE"""
    x = f"(({col} * 395937 + 12345) % 1073741824)"
    ch = [f"substr('{ALPHABET}', (({x} >> {5 * k}) & 31)::int + 1, 1)" for k in range(5, -1, -1)]
    return f"'L0' || {ch[0]} || {ch[1]} || '-' || {' || '.join(ch[2:])}"


def generate(db: Session, *, scale: float, seed: int = 42, days: int = 365) -> dict[str, int]:
    n_cust = round(12_000 * scale)
    n_org = max(3, round(60 * scale))
    n_ev = max(20, round(400 * scale))
    n_ord = round(100_000 * scale)
    p = {"nc": n_cust, "no": n_org, "ne": n_ev, "nord": n_ord, "days": days, "d": EMAIL_DOMAIN,
         "sp": SLUG_PREFIX, "op": ORDER_PREFIX}
    ex = lambda sql, **kw: db.execute(text(sql), p | kw)  # noqa: E731

    clear(db)
    ex("SELECT setseed(:s)", s=(seed % 1000) / 1000)
    pw = hash_password(PASSWORD)  # băm MỘT lần, mọi tài khoản sinh ra dùng chung

    # 1. Khách + Ban tổ chức
    # Họ tên tiếng Việt ghép từ họ / đệm / tên (chọn theo số thứ tự, có dấu); email liên hệ không dấu ở các nhà
    # cung cấp phổ biến; SĐT '03' + hoán vị 8 chữ số (nhân 7919 mod 10^8) → duy nhất nhưng trông ngẫu nhiên.
    # Email TÀI KHOẢN giữ đuôi @lon.ticketnhip.vn để dọn được; đơn hàng dùng email liên hệ (buyer_email).
    ex("""INSERT INTO users (name, email, phone, password_hash, role, created_at)
          SELECT n.ho || ' ' || n.dem || ' ' || n.ten, 'khach' || g || :d,
                 '03' || lpad(((g::bigint * 7919) % 100000000)::text, 8, '0'), :pw, 'customer',
                 now() - make_interval(days => :days + 30) - make_interval(secs => random() * 200 * 86400)
          FROM generate_series(1, :nc) g
          CROSS JOIN LATERAL (SELECT (CAST(:ho AS text[]))[1 + g % :nho] AS ho,
                                     (CAST(:dem AS text[]))[1 + (g / :nho) % :ndem] AS dem,
                                     (CAST(:ten AS text[]))[1 + (g * 7) % :nten] AS ten) n""",
       pw=pw, ho=[h for h, _ in HO], nho=len(HO), dem=DEM, ndem=len(DEM), ten=[t for t, _ in TEN], nten=len(TEN))
    ex("""INSERT INTO users (name, email, phone, password_hash, role, created_at)
          SELECT 'Ban tổ chức ' || g, 'btc' || g || :d, '0898' || lpad(g::text, 6, '0'), :pw, 'organizer',
                 now() - make_interval(days => :days + 60)
          FROM generate_series(1, :no) g""", pw=pw)
    ex("""INSERT INTO organizers (user_id, org_name, phone, created_at)
          SELECT id, 'Công ty Sự kiện ' || initcap(split_part(email, '@', 1)), phone, created_at
          FROM users WHERE role = 'organizer' AND email LIKE '%' || :d""")

    # 2. Sự kiện (k = g mod 20 quyết định phase): 0 chờ duyệt · 1 bị trả lại · 2 đã huỷ · 3 sắp mở bán ·
    #    4–7 đang bán · 8–19 đã diễn (suất 1…days−80 ngày trước để cửa sổ bán vẫn nằm trong 12 tháng)
    ex("DROP TABLE IF EXISTS tl_ev, tl_tier, tl_ord, tl_line")
    ex("""CREATE TEMP TABLE tl_ev AS
          WITH orgs AS (SELECT array_agg(o.user_id ORDER BY o.user_id) a FROM organizers o
                        JOIN users u ON u.id = o.user_id WHERE u.email LIKE '%' || :d),
               cats AS (SELECT array_agg(id ORDER BY id) a FROM categories),
               base AS (SELECT g, g % 20 AS k, random() AS r FROM generate_series(1, :ne) g)
          SELECT g, k, NULL::int AS id, :sp || 'su-kien-' || g AS slug,
                 (SELECT a FROM orgs)[1 + g % :no] AS organizer_id,
                 (SELECT a FROM cats)[1 + g % cardinality((SELECT a FROM cats))] AS category_id,
                 (CAST(:cities AS text[]))[1 + g % :ncity] AS city, (CAST(:venues AS text[]))[1 + g % :nvenue] AS venue,
                 (CAST(:topics AS text[]))[1 + g % :ntopic] || ' số ' || g AS title,
                 (ARRAY[150000, 200000, 250000, 300000, 350000])[1 + g % 5] AS base_price,
                 (date_trunc('day', now() AT TIME ZONE 'Asia/Ho_Chi_Minh')
                   + make_interval(days => CASE WHEN k >= 8 THEN -(1 + floor(r * (:days - 80)))::int
                                                WHEN k = 3 THEN 40 + floor(r * 60)::int
                                                ELSE 5 + floor(r * 55)::int END)
                   + interval '19 hours 30 minutes') AT TIME ZONE 'Asia/Ho_Chi_Minh' AS starts_at
          FROM base""",
       cities=CITIES, ncity=len(CITIES), venues=VENUES, nvenue=len(VENUES), topics=TOPICS, ntopic=len(TOPICS))
    ex("""INSERT INTO events (slug, title, search_text, category_id, city, venue, address, layout, organizer_id,
                             description, notes, status, reject_reason, sale_start, created_at, reviewed_at,
                             cancel_reason, cancelled_at, cancelled_by)
          SELECT slug, title, lower(title || ' ' || city || ' ' || venue), category_id, city, venue,
                 venue || ', ' || city, 'list', organizer_id,
                 ARRAY['Sự kiện sinh tự động cho bộ dữ liệu lớn.'], '{}',
                 CASE k WHEN 0 THEN 'pending' WHEN 1 THEN 'rejected' WHEN 2 THEN 'cancelled' ELSE 'approved' END,
                 CASE WHEN k = 1 THEN 'Thiếu giấy phép biểu diễn' END,
                 CASE WHEN k = 3 THEN now() + make_interval(days => 3 + g % 7) END,
                 starts_at - interval '100 days',
                 CASE WHEN k <> 0 THEN starts_at - interval '99 days' END,
                 CASE WHEN k = 2 THEN 'Nghệ sĩ huỷ lịch biểu diễn' END,
                 CASE WHEN k = 2 THEN now() - make_interval(days => 1 + g % 3) END,
                 CASE WHEN k = 2 THEN (ARRAY['organizer', 'admin'])[1 + g % 2] END
          FROM tl_ev ORDER BY g""")
    ex("UPDATE tl_ev SET id = e.id FROM events e WHERE e.slug = tl_ev.slug")
    ex("""INSERT INTO shows (event_id, id, starts_at, end_time)
          SELECT id, to_char(starts_at AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMMDD-HH24MI'), starts_at, '22:00' FROM tl_ev""")
    ex("""CREATE TEMP TABLE tl_tier AS
          SELECT e.id AS event_id, 've-' || t.n AS tier_id, t.name, e.base_price * t.mult AS price, t.n AS sort_order
          FROM tl_ev e CROSS JOIN (VALUES (1, 'Vé phổ thông', 1), (2, 'Vé VIP', 2), (3, 'Vé VVIP', 4)) AS t(n, name, mult)""")
    ex("""INSERT INTO ticket_tiers (event_id, id, name, price, capacity, max_per_order, perks, sort_order)
          SELECT event_id, tier_id, name, price, 0, 10, '', sort_order FROM tl_tier""")  # sức chứa đặt sau khi có vé

    # 3. Đơn hàng: sự kiện bán được = đã huỷ (trước khi huỷ) / đang bán / đã diễn; độ phổ biến lệch (power) để
    #    bảng xếp hạng có ý nghĩa; ngày mua dồn về gần giờ diễn, ~30 % dời về thứ Bảy liền trước (cuối tuần đông)
    ex("""CREATE TEMP TABLE tl_ord AS
          WITH sales AS (SELECT array_agg(g ORDER BY g) a FROM tl_ev WHERE k = 2 OR k >= 4),
               pick AS (SELECT g, (SELECT a FROM sales)[1 + floor(power(random(), 1.6)
                                    * cardinality((SELECT a FROM sales)))::int] AS eg,
                               random() AS r_t, random() AS r_w, random() AS r_s, random() AS r_r, random() AS r_m,
                               1 + floor(random() * :nc)::int AS cust
                        FROM generate_series(1, :nord) g),
               win AS (SELECT p.*, e.id AS event_id, e.k, e.starts_at,
                              greatest(e.starts_at - interval '99 days', now() - make_interval(days => :days)) AS w0,
                              least(e.starts_at - interval '2 hours', now(),
                                    CASE WHEN e.k = 2 THEN now() - make_interval(days => 1 + e.g % 3) - interval '1 hour'
                                    END) AS w1
                       FROM pick p JOIN tl_ev e ON e.g = p.eg),
               t AS (SELECT w.*, w1 - (w1 - w0) * power(r_t, 2.2) AS t0 FROM win w)
          SELECT g, :op || lpad(g::text, 8, '0') AS id, event_id, k, starts_at, cust,
                 greatest(w0, CASE WHEN r_w < 0.3
                                   THEN t0 - make_interval(days => ((extract(dow FROM t0 AT TIME ZONE 'Asia/Ho_Chi_Minh')::int + 1) % 7))
                                   ELSE t0 END) AS created_at,
                 CASE WHEN k = 2 OR r_s < 0.04 THEN 'refunded' ELSE 'paid' END AS status,
                 r_r, (ARRAY['qr', 'wallet', 'card'])[1 + floor(r_m * 3)::int] AS method
          FROM t""")
    ex("""CREATE TEMP TABLE tl_line AS
          SELECT o.id AS order_id, o.event_id, 've-' || ((o.start + i) % 3 + 1) AS tier_id,
                 1 + floor(power(random(), 2) * 4)::int AS qty
          FROM (SELECT id, event_id, 1 + (random() < 0.25)::int + (random() < 0.08)::int AS n,
                       CASE WHEN random() < 0.6 THEN 0 WHEN random() < 0.7 THEN 1 ELSE 2 END AS start
                FROM tl_ord) o
          CROSS JOIN LATERAL generate_series(0, o.n - 1) i""")
    coupon = db.execute(text("SELECT code, amount, min_order FROM coupons WHERE active ORDER BY code LIMIT 1")).first()
    ex("""INSERT INTO orders (id, user_id, event_id, show_id, subtotal, discount, coupon_code, total, method,
                             buyer_name, buyer_email, buyer_phone, status, created_at, refunded_at)
          WITH sub AS (SELECT l.order_id, sum(t.price * l.qty) AS subtotal FROM tl_line l
                       JOIN tl_tier t ON t.event_id = l.event_id AND t.tier_id = l.tier_id GROUP BY l.order_id),
               cust AS (SELECT row_number() OVER (ORDER BY id) AS n, id, name, phone,
                               (CAST(:ten_ascii AS text[]))[1 + (g * 7) % :nten] || '.'
                               || (CAST(:ho_ascii AS text[]))[1 + g % :nho] || g
                               || (CAST(:mail AS text[]))[1 + g % :nmail] AS contact
                        FROM (SELECT u.*, substring(u.email FROM '^khach([0-9]+)@')::int AS g FROM users u
                              WHERE role = 'customer' AND email LIKE '%' || :d) u),
               o AS (SELECT o.*, s.subtotal, (CAST(:ccode AS varchar) IS NOT NULL AND o.r_r > 0.88 AND s.subtotal >= :cmin
                                             AND s.subtotal >= :camount) AS use_coupon
                     FROM tl_ord o JOIN sub s ON s.order_id = o.id)
          SELECT o.id, c.id, o.event_id, sh.id, o.subtotal,
                 CASE WHEN use_coupon THEN :camount ELSE 0 END, CASE WHEN use_coupon THEN CAST(:ccode AS varchar) END,
                 o.subtotal - CASE WHEN use_coupon THEN :camount ELSE 0 END, o.method,
                 c.name, c.contact, c.phone, o.status, o.created_at,
                 CASE WHEN o.status = 'refunded' THEN
                      CASE WHEN o.k = 2 THEN e.cancelled_at
                           ELSE o.created_at + (least(now(), o.starts_at) - o.created_at) * o.r_r END END
          FROM o JOIN cust c ON c.n = o.cust JOIN shows sh ON sh.event_id = o.event_id
          JOIN events e ON e.id = o.event_id
          ORDER BY o.g""",
       ten_ascii=[a for _, a in TEN], ho_ascii=[a for _, a in HO], nten=len(TEN), nho=len(HO), mail=MAILS,
       nmail=len(MAILS), ccode=coupon.code if coupon else None, camount=coupon.amount if coupon else 0,
       cmin=coupon.min_order if coupon else 0)
    ex("""INSERT INTO order_items (order_id, tier_id, event_id, price, qty)
          SELECT l.order_id, l.tier_id, l.event_id, t.price, l.qty FROM tl_line l
          JOIN tl_tier t ON t.event_id = l.event_id AND t.tier_id = l.tier_id ORDER BY l.order_id, l.tier_id""")
    ex(f"""INSERT INTO tickets (code, order_id, event_id, tier_id, price, checked_in_at)
          SELECT {_code_sql('rn')}, order_id, event_id, tier_id, price,
                 CASE WHEN status = 'paid' AND starts_at < now() AND random() < 0.7
                      THEN starts_at - interval '90 minutes' + random() * interval '2 hours' END
          FROM (SELECT row_number() OVER (ORDER BY l.order_id, l.tier_id, n) AS rn, l.order_id, l.event_id, l.tier_id,
                       t.price, o.status, o.starts_at
                FROM tl_line l JOIN tl_tier t ON t.event_id = l.event_id AND t.tier_id = l.tier_id
                JOIN tl_ord o ON o.id = l.order_id CROSS JOIN LATERAL generate_series(1, l.qty) n) x
          ORDER BY rn""")

    # 4. Kho: đã bán = số vé (paid + refunded); sức chứa = đã bán + ~20 % + 20 chỗ trống
    ex("""INSERT INTO tier_stock (event_id, show_id, tier_id, capacity, presold, sold)
          SELECT t.event_id, sh.id, t.tier_id, coalesce(c.n, 0) * 6 / 5 + 20, 0, coalesce(c.n, 0)
          FROM tl_tier t JOIN shows sh ON sh.event_id = t.event_id
          LEFT JOIN (SELECT event_id, tier_id, count(*) AS n FROM tickets WHERE order_id LIKE :op || '%'
                     GROUP BY 1, 2) c ON c.event_id = t.event_id AND c.tier_id = t.tier_id""")
    ex("""UPDATE ticket_tiers tt SET capacity = st.capacity FROM tier_stock st, tl_ev e
          WHERE st.event_id = tt.event_id AND st.tier_id = tt.id AND e.id = tt.event_id""")
    ex("DROP TABLE tl_ev, tl_tier, tl_ord, tl_line")

    # 5. Rút tiền: chỉ trên thực nhận của sự kiện đã diễn (withdrawals.balances), không vượt 85 % số đó
    _withdrawals(db, scale, seed)
    db.flush()
    return _counts_by_marker(db)


def _withdrawals(db: Session, scale: float, seed: int) -> None:
    from app.services import withdrawals

    orgs = [r[0] for r in db.execute(text("SELECT o.user_id FROM organizers o JOIN users u ON u.id = o.user_id "
                                          "WHERE u.email LIKE :d ORDER BY o.user_id"), {"d": f"%{EMAIL_DOMAIN}"})]
    if not orgs:
        return
    now = db.execute(text("SELECT now()")).scalar()
    per_org = max(3, round(1000 * scale / len(orgs)))
    rows = []
    for i, (org, bal) in enumerate(sorted(withdrawals.balances(db, orgs).items())):
        rnd = random.Random(seed * 1000 + i)
        budget = bal["settledNet"] * 85 // 100
        k = min(per_org, budget // 50_000)  # mỗi khoản ≥ 50.000 ₫, tổng ≤ budget
        if k < 3:
            continue
        step = budget // k
        for j in range(k):
            amount = max(50_000, (int(step * rnd.uniform(0.6, 1.0)) // 1000) * 1000)
            status = "pending" if j == k - 1 else "rejected" if j % 10 == 1 else "paid"
            created = now - timedelta(days=300 * (k - j) / k, hours=rnd.uniform(0, 12))
            done = None if status == "pending" else created + timedelta(days=rnd.uniform(0.2, 3))
            rows.append({"o": org, "a": amount, "s": status, "c": created, "p": done,
                         "n": "Sai thông tin tài khoản ngân hàng" if status == "rejected" else None})
    if rows:
        db.execute(text("""INSERT INTO withdrawals (organizer_id, amount, bank_name, account_no, account_name, status,
                                                    note, created_at, processed_at)
                           VALUES (:o, :a, 'Vietcombank', '0011223344', 'CONG TY SU KIEN', :s, :n, :c, :p)"""), rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh bộ dữ liệu lớn (mô phỏng 12 tháng) để đo hiệu năng")
    parser.add_argument("--scale", type=float, default=1.0, help="1.0 = 100 000 đơn, 12 000 khách, 400 sự kiện")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--database-url", default=settings.database_url)
    args = parser.parse_args()

    engine = make_engine(args.database_url)
    engine.echo = False
    t0 = time.perf_counter()
    with Session(engine) as db:
        added = generate(db, scale=args.scale, seed=args.seed)
        db.commit()
        counts = row_counts(db)
    print(f"Đã sinh trong {time.perf_counter() - t0:.1f}s: {added}")
    print("Số dòng mọi bảng:", counts)


if __name__ == "__main__":
    main()
