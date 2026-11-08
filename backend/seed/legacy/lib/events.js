/* ==========================================================================
   KHO SỰ KIỆN DÙNG CHUNG
   Gom sự kiện từ mọi nguồn dữ liệu trang chủ (hero, featured, poster,
   catalog, lịch diễn…) thành một danh sách thống nhất, tra cứu theo slug.
   Thẻ nào có cùng tên sự kiện sẽ trỏ về cùng một trang chi tiết.
   ========================================================================== */
import { categories } from '../data/navigation.js'
import { heroBanners } from '../data/hero.js'
import { featuredEvents, posters, resaleTickets, trendingEvents } from '../data/home.js'
import { catalog, schedules } from '../data/discover.js'
import { eventDetails } from '../data/eventDetails.js'
import { MAX_PER_ORDER } from '../data/rules.js'
import { ZONE_MAPS, getSeatMap } from '../data/venueMaps.js'
import { normalizeVi } from './utils.js'

/* ---------- Đường dẫn ---------- */
export const slugify = (s = '') =>
  normalizeVi(s)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

export const eventPath = (title) => `/su-kien/${slugify(title)}`
export const bookingPath = (slug, showId) => `/su-kien/${slug}/dat-ve${showId ? `?suat=${showId}` : ''}`

/* ---------- Tiện ích ---------- */
const hash = (s) => {
  let h = 0
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return h
}
const pad = (n) => String(n).padStart(2, '0')

/** Tháng 11–12 thuộc năm 2026, các tháng còn lại thuộc 2027 */
const yearFor = (month) => (month >= 11 ? 2026 : 2027)

/** Đọc "02.01.2027" | "21 Th 11" | "28.11" → Date */
const parseDate = (str = '') => {
  let m = str.match(/(\d{1,2})\.(\d{1,2})\.(\d{4})/)
  if (m) return new Date(+m[3], +m[2] - 1, +m[1])
  m = str.match(/(\d{1,2})\s*Th\s*(\d{1,2})/i)
  if (m) return new Date(yearFor(+m[2]), +m[2] - 1, +m[1])
  m = str.match(/(\d{1,2})\.(\d{1,2})/)
  if (m) return new Date(yearFor(+m[2]), +m[2] - 1, +m[1])
  return undefined
}

/** "Nhà hát [ĐỊA ĐIỂM], TP.HCM" | "… · Hà Nội" → { venue, city } */
const splitPlace = (s = '') => {
  const m = s.match(/^(.*?)(?:\s·\s|,\s)([^,·]+)$/)
  return m ? { venue: m[1].trim(), city: m[2].trim() } : { venue: s.trim() || undefined }
}

const statusOf = (s = '') => (/SẮP/.test(s) ? 'coming' : 'on-sale')

const guessCategory = (text) => {
  const t = normalizeVi(text)
  if (/kich|vo dien|cai luong|hai kich|san khau/.test(t)) return 'san-khau'
  if (/trien lam|di san|tour/.test(t)) return 'tham-quan'
  if (/workshop|hoi thao/.test(t)) return 'hoi-thao'
  return 'nhac-song'
}

/* ---------- Gom dữ liệu thô ---------- */
const raw = new Map()
const add = (title, data) => {
  const slug = slugify(title)
  const cur = raw.get(slug) || { title }
  for (const [k, v] of Object.entries(data)) {
    if (v !== undefined && v !== null && v !== '' && cur[k] === undefined) cur[k] = v
  }
  raw.set(slug, cur)
}

// Thứ tự ưu tiên: thông tin chi tiết > catalog > hero > featured > lịch diễn > còn lại
eventDetails.forEach((d) => add(d.title, d))
catalog.forEach((e) => add(e.title, { city: e.city, date: parseDate(e.date), price: e.price, category: e.category }))
heroBanners.forEach((b) =>
  add(b.title, {
    ...splitPlace(b.venue),
    date: parseDate(`${b.day} Th ${b.month.replace(/\D/g, '')}`),
    time: b.time,
    status: statusOf(b.status),
  }),
)
;[...featuredEvents.upcoming, ...featuredEvents.new].forEach((e) =>
  add(e.title, { ...splitPlace(e.venue), date: parseDate(e.date), time: e.time, status: statusOf(e.status) }),
)
schedules.weekend.items.forEach((i) =>
  add(i.title, { venue: i.venue, date: new Date(2026, 10, i.day === 'CN' ? 8 : 7), time: i.time, price: i.price }),
)
schedules.month.items.forEach((i) => add(i.title, { venue: i.venue, date: parseDate(i.day), time: i.time, price: i.price }))
trendingEvents.forEach((t) => add(t.title, { date: parseDate(t.date) }))
posters.forEach((p) => add(p.title, { date: parseDate(p.date), tag: p.tag }))
resaleTickets.forEach((r) => {
  const [city, d] = r.meta.split(' · ')
  add(r.title, { city, date: parseDate(d), resaleCount: r.count })
})

/* ---------- Sinh thông tin mặc định ---------- */
const roundK = (n) => Math.round(n / 10) * 10 * 1000

const makeTiers = (baseK, h) => [
  { id: 'pho-thong', name: 'Phổ thông', price: baseK * 1000, perks: 'Khu vực phổ thông, vào cửa theo thứ tự check-in.', remaining: 40 + (h % 160), max: 6 },
  { id: 'vip', name: 'VIP', price: roundK(baseK * 1.8), perks: 'Khu vực gần sân khấu, lối vào riêng, quà lưu niệm.', remaining: 5 + (h % 30), max: 4 },
  { id: 'svip', name: 'SVIP', price: roundK(baseK * 3), perks: 'Hàng ghế đầu, check-in sớm 60 phút, giao lưu cùng nghệ sĩ.', remaining: h % 4 === 0 ? 0 : 1 + (h % 9), max: 2 },
]

const defaultDescription = (title, venue, city) => [
  `${title} là một trong những sự kiện được mong chờ nhất mùa này tại ${city}. Chương trình được đầu tư kỹ lưỡng từ nội dung, âm thanh đến không gian tại ${venue}.`,
  'Khán giả sẽ được trải nghiệm trọn vẹn không khí của buổi diễn trực tiếp, cùng nhiều hoạt động bên lề và quà tặng dành cho những người đến sớm.',
  'Số lượng vé có hạn và được phân phối chính thức qua TicketNhịp. Vé điện tử kèm mã QR sẽ được gửi ngay sau khi thanh toán thành công.',
]

export const DEFAULT_NOTES = [
  'Vé đã mua không hỗ trợ đổi, trả hoặc hoàn tiền (trừ trường hợp sự kiện bị huỷ).',
  'Trẻ em dưới 8 tuổi không được tham gia; từ 8–16 tuổi cần có người lớn đi kèm.',
  'Vui lòng mang theo giấy tờ tuỳ thân và mã QR khi check-in.',
  'Không mang theo đồ ăn, nước uống, vật sắc nhọn và thiết bị quay chụp chuyên nghiệp.',
]

const CAT = Object.fromEntries(categories.map((c) => [c.id, c]))

function finalize(slug, r) {
  const h = hash(slug)
  const category = r.category || guessCategory(`${r.title} ${r.tag || ''}`)
  const city = r.city || ['TP.HCM', 'Hà Nội', 'Đà Lạt'][h % 3]
  const venue = r.venue || `[ĐỊA ĐIỂM] ${city}`
  const date = r.date || new Date(2026, 11, 5 + (h % 20))
  const defaultTime = r.time || ['19:00', '19:30', '20:00'][h % 3]

  // Suất diễn: mặc định 1 suất; eventDetails có thể khai báo nhiều suất
  const shows = (r.shows || [{ date, time: defaultTime, endTime: r.endTime }])
    .map((s) => {
      const d = typeof s.date === 'string' ? new Date(`${s.date}T00:00:00`) : new Date(s.date)
      const [hh, mm] = s.time.split(':').map(Number)
      d.setHours(hh, mm, 0, 0)
      return { id: showIdOf(d), start: d, startTime: s.time, endTime: s.endTime || `${pad(Math.min(hh + 3, 23))}:${pad(mm)}` }
    })
    .sort((a, b) => a.start - b.start)
  const { start, startTime, endTime } = shows[0]

  // Kiểu bán vé: 'zones' (sơ đồ khu vực) | 'seats' (chọn ghế) | 'list' (chỉ chọn loại vé)
  const layout = r.layout || 'list'
  let tiers
  if (layout === 'zones') {
    const map = ZONE_MAPS[r.map]
    tiers = map.zones.map((z) => {
      const g = map.groups[z.group]
      return { id: z.id, name: z.label, group: z.group, groupLabel: g.label, color: g.color, price: r.prices[z.group], capacity: z.cap, remaining: z.cap, max: g.max ?? 6, perks: g.perks }
    })
  } else if (layout === 'seats') {
    const sm = getSeatMap(r.map)
    tiers = Object.entries(sm.groups).map(([gid, g]) => {
      const count = sm.seats.filter((s) => s.group === gid).length
      return { id: gid, name: g.label, group: gid, groupLabel: g.label, color: g.color, price: r.prices[gid], capacity: count, remaining: count, max: MAX_PER_ORDER, perks: g.perks }
    })
  } else {
    tiers = r.tiers || makeTiers(r.price || [350, 450, 600, 800, 990][h % 5], h)
  }

  return {
    slug,
    title: r.title,
    category,
    categoryLabel: CAT[category]?.label || 'Khác',
    marker: CAT[category]?.dot || 'bg-ink',
    city,
    venue,
    address: r.address || `[ĐỊA CHỈ], ${city}`,
    start,
    startTime,
    endTime,
    shows,
    layout,
    map: r.map || null,
    status: r.status || 'on-sale',
    saleOpensAt: r.saleOpensAt || new Date(2026, 10, 20, 10, 0),
    organizer: r.organizer || {
      name: '[BAN TỔ CHỨC]',
      bio: 'Đơn vị tổ chức sự kiện đối tác chính thức của TicketNhịp.',
    },
    description: r.description || defaultDescription(r.title, venue, city),
    notes: r.notes || DEFAULT_NOTES,
    tiers,
    minPrice: Math.min(...tiers.map((t) => t.price)),
    resaleCount: r.resaleCount || 0,
  }
}

/** Dựng sự kiện từ dữ liệu thô (dùng cho sự kiện do Ban tổ chức tạo, lấy từ máy chủ) */
export const buildEvent = (slug, raw) => finalize(slug, raw)

/* ---------- API ---------- */
export const events = [...raw].map(([slug, r]) => finalize(slug, r))
const bySlug = new Map(events.map((e) => [e.slug, e]))

export const getEvent = (slug) => bySlug.get(slug)

/** Sự kiện liên quan: ưu tiên cùng danh mục, rồi cùng thành phố */
export const relatedEvents = (ev, n = 4) =>
  events
    .filter((e) => e.slug !== ev.slug)
    .map((e) => ({ e, score: (e.category === ev.category ? 2 : 0) + (e.city === ev.city ? 1 : 0) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, n)
    .map(({ e }) => e)

/** Chuyển sự kiện → dữ liệu cho TicketCard / SquareEventCard */
export const toCardItem = (e) => ({
  id: e.slug,
  slug: e.slug,
  title: e.title,
  city: e.city,
  date: `${pad(e.start.getDate())} Th ${e.start.getMonth() + 1}`,
  price: e.minPrice / 1000,
})

/** Tìm kiếm không dấu theo tên, thành phố, địa điểm */
export const searchEvents = (query) => {
  const q = normalizeVi(query)
  return events.filter((e) => normalizeVi(`${e.title} ${e.city} ${e.venue} ${e.categoryLabel}`).includes(q))
}

/** Mã suất diễn từ thời điểm bắt đầu: "20261115-1900" */
export function showIdOf(d) {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`
}

/** Gom hạng vé theo nhóm giá (vd. CAT 1A + CAT 1B → CAT 1) để hiển thị bảng giá */
export function priceGroups(tiers) {
  const m = new Map()
  for (const t of tiers) {
    const key = t.group || t.id
    const g = m.get(key) || { id: key, label: t.groupLabel || t.name, color: t.color, price: t.price, remaining: 0, zones: [], perks: t.perks }
    g.remaining += t.remaining
    g.zones.push(t.name)
    g.price = Math.min(g.price, t.price)
    m.set(key, g)
  }
  return [...m.values()].sort((a, b) => b.price - a.price)
}

export const LAYOUT_LABEL = { zones: 'Chọn khu vực trên sơ đồ', seats: 'Chọn ghế trên sơ đồ', list: 'Chọn loại vé' }

/* ---------- Định dạng ngày ---------- */
const WEEKDAYS = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy']
export const formatEventDate = (d) => `${WEEKDAYS[d.getDay()]}, ${d.getDate()} tháng ${d.getMonth() + 1}, ${d.getFullYear()}`
export const formatShortDate = (d) => `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`

/** "19:00 – 23:00, Chủ nhật, 15 tháng 11, 2026" */
export const formatShow = (show) => `${show.startTime} – ${show.endTime}, ${formatEventDate(show.start)}`
