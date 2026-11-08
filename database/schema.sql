--
-- PostgreSQL database dump
--

\restrict x1tVl1nTwWWt0pDWoVxOOeh7ENaW7V7vkDQrIXe4ZrScaAg411aQHOzGoYRaTB4

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id character varying(40) NOT NULL,
    label text NOT NULL,
    dot text NOT NULL,
    sort_order integer NOT NULL
);


--
-- Name: TABLE categories; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.categories IS 'Thể loại sự kiện (Nhạc sống, Sân khấu…)';


--
-- Name: coupons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupons (
    code character varying(30) NOT NULL,
    amount integer NOT NULL,
    min_order integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_coupons_amount CHECK ((amount > 0)),
    CONSTRAINT ck_coupons_min_order CHECK ((min_order >= 0))
);


--
-- Name: TABLE coupons; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.coupons IS 'Mã giảm giá: số tiền giảm và giá trị đơn tối thiểu';


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id integer NOT NULL,
    slug character varying(160) NOT NULL,
    title text NOT NULL,
    search_text text NOT NULL,
    category_id character varying(40) NOT NULL,
    city text NOT NULL,
    venue text NOT NULL,
    address text NOT NULL,
    layout character varying(10) NOT NULL,
    map_id character varying(60),
    organizer_id integer,
    host_name text,
    host_bio text,
    description text[] NOT NULL,
    notes text[] NOT NULL,
    status character varying(10) DEFAULT 'approved'::character varying NOT NULL,
    reject_reason text,
    sale_start timestamp with time zone,
    resale_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    reviewed_at timestamp with time zone,
    active boolean DEFAULT true NOT NULL,
    cancel_reason text,
    cancelled_at timestamp with time zone,
    cancelled_by character varying(10),
    CONSTRAINT ck_events_cancel_fields CHECK ((((status)::text = 'cancelled'::text) = ((cancelled_at IS NOT NULL) AND (cancelled_by IS NOT NULL) AND (cancel_reason IS NOT NULL)))),
    CONSTRAINT ck_events_cancelled_by CHECK (((cancelled_by)::text = ANY ((ARRAY['organizer'::character varying, 'admin'::character varying])::text[]))),
    CONSTRAINT ck_events_layout CHECK (((layout)::text = ANY ((ARRAY['list'::character varying, 'zones'::character varying, 'seats'::character varying])::text[]))),
    CONSTRAINT ck_events_layout_map CHECK ((((layout)::text = 'list'::text) = (map_id IS NULL))),
    CONSTRAINT ck_events_resale CHECK ((resale_count >= 0)),
    CONSTRAINT ck_events_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE events; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.events IS 'Sự kiện: của sàn (organizer_id NULL) hoặc do Ban tổ chức tạo (chờ duyệt → đã duyệt / bị trả lại)';


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: home_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.home_slots (
    section character varying(30) NOT NULL,
    "position" integer NOT NULL,
    event_id integer NOT NULL,
    meta jsonb NOT NULL,
    CONSTRAINT ck_home_slots_section CHECK (((section)::text = ANY ((ARRAY['hero'::character varying, 'featured-upcoming'::character varying, 'featured-new'::character varying, 'trending'::character varying, 'posters'::character varying, 'resale'::character varying, 'schedule-weekend'::character varying, 'schedule-month'::character varying, 'catalog'::character varying])::text[])))
);


--
-- Name: TABLE home_slots; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.home_slots IS 'Vị trí sự kiện trên các khu của trang chủ; meta chỉ chứa phần trang trí';


--
-- Name: map_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_groups (
    map_id character varying(60) NOT NULL,
    id character varying(60) NOT NULL,
    label text NOT NULL,
    color text NOT NULL,
    ink boolean NOT NULL,
    max_per_order integer,
    perks text NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_map_groups_max CHECK (((max_per_order IS NULL) OR (max_per_order > 0)))
);


--
-- Name: TABLE map_groups; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.map_groups IS 'Nhóm khu / hạng ghế trong một sơ đồ (màu, quyền lợi, số vé tối đa mỗi đơn)';


--
-- Name: map_seats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_seats (
    map_id character varying(60) NOT NULL,
    id character varying(30) NOT NULL,
    section character varying(20) NOT NULL,
    row_label character varying(10) NOT NULL,
    num integer NOT NULL,
    group_id character varying(60) NOT NULL,
    label text NOT NULL,
    x double precision NOT NULL,
    y double precision NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: TABLE map_seats; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.map_seats IS 'Ghế trên sơ đồ ghế (hàng, số, toạ độ)';


--
-- Name: map_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.map_zones (
    map_id character varying(60) NOT NULL,
    id character varying(60) NOT NULL,
    label text NOT NULL,
    group_id character varying(60) NOT NULL,
    capacity integer NOT NULL,
    shape jsonb NOT NULL,
    text jsonb NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_map_zones_capacity CHECK ((capacity > 0))
);


--
-- Name: TABLE map_zones; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.map_zones IS 'Khu vực trên sơ đồ khu (sức chứa, hình vẽ)';


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items (
    order_id character varying(20) NOT NULL,
    tier_id character varying(60) NOT NULL,
    event_id integer NOT NULL,
    price integer NOT NULL,
    qty integer NOT NULL,
    CONSTRAINT ck_order_items_price CHECK ((price >= 0)),
    CONSTRAINT ck_order_items_qty CHECK ((qty > 0))
);


--
-- Name: TABLE order_items; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.order_items IS 'Dòng đơn hàng: hạng vé × số lượng, price là giá tại thời điểm mua';


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    id character varying(20) NOT NULL,
    user_id integer NOT NULL,
    event_id integer NOT NULL,
    show_id character varying(13) NOT NULL,
    subtotal integer NOT NULL,
    discount integer DEFAULT 0 NOT NULL,
    coupon_code character varying(30),
    total integer NOT NULL,
    method character varying(10) NOT NULL,
    buyer_name text NOT NULL,
    buyer_email character varying(254) NOT NULL,
    buyer_phone character varying(20) NOT NULL,
    status character varying(10) DEFAULT 'paid'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    refunded_at timestamp with time zone,
    CONSTRAINT ck_orders_method CHECK (((method)::text = ANY ((ARRAY['qr'::character varying, 'wallet'::character varying, 'card'::character varying])::text[]))),
    CONSTRAINT ck_orders_refunded_at CHECK (((refunded_at IS NULL) OR ((status)::text = 'refunded'::text))),
    CONSTRAINT ck_orders_status CHECK (((status)::text = ANY ((ARRAY['paid'::character varying, 'refunded'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_orders_total CHECK (((total = (subtotal - discount)) AND (discount >= 0) AND (total >= 0)))
);


--
-- Name: TABLE orders; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orders IS 'Đơn hàng; total = subtotal − discount (Ban tổ chức chịu giảm giá)';


--
-- Name: organizers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizers (
    user_id integer NOT NULL,
    org_name text NOT NULL,
    phone character varying(20) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE organizers; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organizers IS 'Hồ sơ Ban tổ chức; 1 tài khoản = 1 đơn vị tổ chức';


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_resets (
    token_hash character varying(64) NOT NULL,
    user_id integer NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE password_resets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.password_resets IS 'Yêu cầu đặt lại mật khẩu (token băm, hạn dùng, đã dùng chưa)';


--
-- Name: seat_holds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seat_holds (
    event_id integer NOT NULL,
    show_id character varying(13) NOT NULL,
    seat_id character varying(30) NOT NULL,
    order_id character varying(20)
);


--
-- Name: TABLE seat_holds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.seat_holds IS 'Ghế đã bán theo suất; order_id NULL = đã bán sẵn. Khoá chính chặn bán trùng ghế';


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessions (
    token_hash character varying(64) NOT NULL,
    user_id integer NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sessions IS 'Phiên đăng nhập; chỉ lưu SHA-256 của token, không lưu token gốc';


--
-- Name: shows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shows (
    event_id integer NOT NULL,
    id character varying(13) NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    end_time time without time zone NOT NULL,
    active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE shows; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.shows IS 'Suất diễn của sự kiện; id dạng YYYYMMDD-HHMM theo giờ Việt Nam';


--
-- Name: ticket_tiers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_tiers (
    event_id integer NOT NULL,
    id character varying(60) NOT NULL,
    name text NOT NULL,
    price integer NOT NULL,
    capacity integer NOT NULL,
    max_per_order integer NOT NULL,
    perks text NOT NULL,
    group_id character varying(60),
    sort_order integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_ticket_tiers_capacity CHECK ((capacity >= 0)),
    CONSTRAINT ck_ticket_tiers_max CHECK ((max_per_order > 0)),
    CONSTRAINT ck_ticket_tiers_price CHECK ((price >= 0))
);


--
-- Name: TABLE ticket_tiers; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ticket_tiers IS 'Hạng vé của sự kiện (với sơ đồ khu/ghế: mỗi khu hoặc hạng ghế là một hạng)';


--
-- Name: tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tickets (
    code character varying(20) NOT NULL,
    order_id character varying(20) NOT NULL,
    event_id integer NOT NULL,
    tier_id character varying(60) NOT NULL,
    price integer NOT NULL,
    seat_id character varying(30),
    checked_in_at timestamp with time zone,
    CONSTRAINT ck_tickets_price CHECK ((price >= 0))
);


--
-- Name: TABLE tickets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tickets IS 'Vé điện tử; mỗi vé một mã check-in riêng';


--
-- Name: tier_stock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tier_stock (
    event_id integer NOT NULL,
    show_id character varying(13) NOT NULL,
    tier_id character varying(60) NOT NULL,
    capacity integer NOT NULL,
    presold integer DEFAULT 0 NOT NULL,
    sold integer DEFAULT 0 NOT NULL,
    CONSTRAINT ck_tier_stock_capacity CHECK (((presold + sold) <= capacity)),
    CONSTRAINT ck_tier_stock_nonneg CHECK (((presold >= 0) AND (sold >= 0)))
);


--
-- Name: TABLE tier_stock; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tier_stock IS 'Kho vé theo suất + hạng: presold (bán sẵn trước khi hệ thống chạy) + sold (bán qua hệ thống) ≤ capacity';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name text NOT NULL,
    email character varying(254),
    phone character varying(20),
    password_hash text NOT NULL,
    role character varying(10) DEFAULT 'customer'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_users_contact CHECK (((email IS NOT NULL) OR (phone IS NOT NULL))),
    CONSTRAINT ck_users_role CHECK (((role)::text = ANY ((ARRAY['customer'::character varying, 'organizer'::character varying, 'admin'::character varying])::text[])))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS 'Tài khoản: khách (customer), Ban tổ chức (organizer), quản trị sàn (admin)';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: v_daily_revenue; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_daily_revenue AS
 SELECT e.organizer_id,
    ((o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh'::text))::date AS day,
    sum(o.total) AS revenue,
    (sum(( SELECT COALESCE(sum(i.qty), (0)::bigint) AS "coalesce"
           FROM public.order_items i
          WHERE ((i.order_id)::text = (o.id)::text))))::bigint AS tickets
   FROM (public.orders o
     JOIN public.events e ON ((e.id = o.event_id)))
  WHERE ((o.status)::text = 'paid'::text)
  GROUP BY e.organizer_id, (((o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh'::text))::date);


--
-- Name: VIEW v_daily_revenue; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_daily_revenue IS 'Doanh thu (tiền khách trả) và số vé theo ngày giờ Việt Nam, theo Ban tổ chức (NULL = sự kiện của sàn)';


--
-- Name: v_event_sales; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_event_sales AS
 SELECT o.event_id,
    o.show_id,
    i.tier_id,
    sum(i.qty) AS sold,
    sum((i.price * i.qty)) AS revenue
   FROM (public.order_items i
     JOIN public.orders o ON (((o.id)::text = (i.order_id)::text)))
  WHERE ((o.status)::text = 'paid'::text)
  GROUP BY o.event_id, o.show_id, i.tier_id;


--
-- Name: VIEW v_event_sales; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_event_sales IS 'Số vé đã bán và doanh thu (giá × số lượng) theo sự kiện, suất, hạng — chỉ đơn đã thanh toán';


--
-- Name: venue_maps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.venue_maps (
    id character varying(60) NOT NULL,
    kind character varying(10) NOT NULL,
    name text NOT NULL,
    view_box text,
    decor jsonb NOT NULL,
    CONSTRAINT ck_venue_maps_kind CHECK (((kind)::text = ANY ((ARRAY['zones'::character varying, 'seats'::character varying])::text[])))
);


--
-- Name: TABLE venue_maps; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.venue_maps IS 'Sơ đồ địa điểm: sơ đồ khu vực (zones) hoặc sơ đồ ghế (seats)';


--
-- Name: withdrawals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.withdrawals (
    id integer NOT NULL,
    organizer_id integer NOT NULL,
    amount integer NOT NULL,
    bank_name text NOT NULL,
    account_no character varying(20) NOT NULL,
    account_name text NOT NULL,
    status character varying(10) DEFAULT 'pending'::character varying NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    processed_by integer,
    CONSTRAINT ck_withdrawals_amount CHECK ((amount > 0)),
    CONSTRAINT ck_withdrawals_processed CHECK ((((status)::text = 'pending'::text) = (processed_at IS NULL))),
    CONSTRAINT ck_withdrawals_reject_note CHECK ((((status)::text <> 'rejected'::text) OR (note IS NOT NULL))),
    CONSTRAINT ck_withdrawals_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'paid'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: TABLE withdrawals; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.withdrawals IS 'Yêu cầu rút tiền của Ban tổ chức: chờ xử lý → Admin đánh dấu đã chuyển hoặc từ chối (kèm lý do)';


--
-- Name: withdrawals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.withdrawals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: withdrawals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.withdrawals_id_seq OWNED BY public.withdrawals.id;


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: withdrawals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdrawals ALTER COLUMN id SET DEFAULT nextval('public.withdrawals_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: coupons coupons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupons
    ADD CONSTRAINT coupons_pkey PRIMARY KEY (code);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: events events_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_slug_key UNIQUE (slug);


--
-- Name: home_slots home_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.home_slots
    ADD CONSTRAINT home_slots_pkey PRIMARY KEY (section, "position");


--
-- Name: map_groups map_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_groups
    ADD CONSTRAINT map_groups_pkey PRIMARY KEY (map_id, id);


--
-- Name: map_seats map_seats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_seats
    ADD CONSTRAINT map_seats_pkey PRIMARY KEY (map_id, id);


--
-- Name: map_zones map_zones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_zones
    ADD CONSTRAINT map_zones_pkey PRIMARY KEY (map_id, id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (order_id, tier_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: organizers organizers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizers
    ADD CONSTRAINT organizers_pkey PRIMARY KEY (user_id);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (token_hash);


--
-- Name: seat_holds seat_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_holds
    ADD CONSTRAINT seat_holds_pkey PRIMARY KEY (event_id, show_id, seat_id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (token_hash);


--
-- Name: shows shows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_pkey PRIMARY KEY (event_id, id);


--
-- Name: ticket_tiers ticket_tiers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_tiers
    ADD CONSTRAINT ticket_tiers_pkey PRIMARY KEY (event_id, id);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (code);


--
-- Name: tier_stock tier_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tier_stock
    ADD CONSTRAINT tier_stock_pkey PRIMARY KEY (event_id, show_id, tier_id);


--
-- Name: orders uq_orders_id_event; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT uq_orders_id_event UNIQUE (id, event_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: venue_maps venue_maps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venue_maps
    ADD CONSTRAINT venue_maps_pkey PRIMARY KEY (id);


--
-- Name: withdrawals withdrawals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdrawals
    ADD CONSTRAINT withdrawals_pkey PRIMARY KEY (id);


--
-- Name: ix_events_organizer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_events_organizer_id ON public.events USING btree (organizer_id);


--
-- Name: ix_orders_buyer_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_buyer_trgm ON public.orders USING gin (lower((((((((id)::text || ' '::text) || buyer_name) || ' '::text) || (buyer_email)::text) || ' '::text) || (buyer_phone)::text)) public.gin_trgm_ops);


--
-- Name: ix_orders_event_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_event_created ON public.orders USING btree (event_id, created_at);


--
-- Name: ix_orders_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_status_created ON public.orders USING btree (status, created_at) INCLUDE (event_id, total);


--
-- Name: ix_orders_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_user_id ON public.orders USING btree (user_id);


--
-- Name: ix_seat_holds_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seat_holds_order_id ON public.seat_holds USING btree (order_id);


--
-- Name: ix_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: ix_tickets_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tickets_order_id ON public.tickets USING btree (order_id);


--
-- Name: ix_withdrawals_organizer_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_withdrawals_organizer_created ON public.withdrawals USING btree (organizer_id, created_at);


--
-- Name: events events_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id);


--
-- Name: events events_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.venue_maps(id);


--
-- Name: events events_organizer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_organizer_id_fkey FOREIGN KEY (organizer_id) REFERENCES public.organizers(user_id) ON DELETE CASCADE;


--
-- Name: order_items fk_order_items_order_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_items_order_event FOREIGN KEY (order_id, event_id) REFERENCES public.orders(id, event_id) ON DELETE CASCADE;


--
-- Name: seat_holds fk_seat_holds_order_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_holds
    ADD CONSTRAINT fk_seat_holds_order_event FOREIGN KEY (order_id, event_id) REFERENCES public.orders(id, event_id) ON DELETE CASCADE;


--
-- Name: tickets fk_tickets_order_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT fk_tickets_order_event FOREIGN KEY (order_id, event_id) REFERENCES public.orders(id, event_id) ON DELETE CASCADE;


--
-- Name: home_slots home_slots_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.home_slots
    ADD CONSTRAINT home_slots_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: map_groups map_groups_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_groups
    ADD CONSTRAINT map_groups_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.venue_maps(id) ON DELETE CASCADE;


--
-- Name: map_seats map_seats_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_seats
    ADD CONSTRAINT map_seats_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.venue_maps(id) ON DELETE CASCADE;


--
-- Name: map_seats map_seats_map_id_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_seats
    ADD CONSTRAINT map_seats_map_id_group_id_fkey FOREIGN KEY (map_id, group_id) REFERENCES public.map_groups(map_id, id) ON DELETE CASCADE;


--
-- Name: map_zones map_zones_map_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_zones
    ADD CONSTRAINT map_zones_map_id_fkey FOREIGN KEY (map_id) REFERENCES public.venue_maps(id) ON DELETE CASCADE;


--
-- Name: map_zones map_zones_map_id_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.map_zones
    ADD CONSTRAINT map_zones_map_id_group_id_fkey FOREIGN KEY (map_id, group_id) REFERENCES public.map_groups(map_id, id) ON DELETE CASCADE;


--
-- Name: order_items order_items_event_id_tier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_event_id_tier_id_fkey FOREIGN KEY (event_id, tier_id) REFERENCES public.ticket_tiers(event_id, id);


--
-- Name: orders orders_coupon_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_coupon_code_fkey FOREIGN KEY (coupon_code) REFERENCES public.coupons(code);


--
-- Name: orders orders_event_id_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_event_id_show_id_fkey FOREIGN KEY (event_id, show_id) REFERENCES public.shows(event_id, id);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: organizers organizers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizers
    ADD CONSTRAINT organizers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: seat_holds seat_holds_event_id_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_holds
    ADD CONSTRAINT seat_holds_event_id_show_id_fkey FOREIGN KEY (event_id, show_id) REFERENCES public.shows(event_id, id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: shows shows_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shows
    ADD CONSTRAINT shows_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: ticket_tiers ticket_tiers_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_tiers
    ADD CONSTRAINT ticket_tiers_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: tickets tickets_event_id_tier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_event_id_tier_id_fkey FOREIGN KEY (event_id, tier_id) REFERENCES public.ticket_tiers(event_id, id);


--
-- Name: tier_stock tier_stock_event_id_show_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tier_stock
    ADD CONSTRAINT tier_stock_event_id_show_id_fkey FOREIGN KEY (event_id, show_id) REFERENCES public.shows(event_id, id) ON DELETE CASCADE;


--
-- Name: tier_stock tier_stock_event_id_tier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tier_stock
    ADD CONSTRAINT tier_stock_event_id_tier_id_fkey FOREIGN KEY (event_id, tier_id) REFERENCES public.ticket_tiers(event_id, id) ON DELETE CASCADE;


--
-- Name: withdrawals withdrawals_organizer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdrawals
    ADD CONSTRAINT withdrawals_organizer_id_fkey FOREIGN KEY (organizer_id) REFERENCES public.organizers(user_id) ON DELETE CASCADE;


--
-- Name: withdrawals withdrawals_processed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.withdrawals
    ADD CONSTRAINT withdrawals_processed_by_fkey FOREIGN KEY (processed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict x1tVl1nTwWWt0pDWoVxOOeh7ENaW7V7vkDQrIXe4ZrScaAg411aQHOzGoYRaTB4

