/* ==========================================================================
   XUẤT DANH MỤC SỰ KIỆN TỪ CODE JS → backend/seed/catalog.json
   Chạy MỘT lần từ gốc dự án (ticketnhip/):
     TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs
   Kết quả: catalog.json (nguồn nạp chính thức cho `python -m app.seed`)
   và bảng "Thẻ thay đổi so với hiện tại" in ra màn hình.
   ========================================================================== */
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

/* ---------- 1. Bắt buộc giờ Việt Nam (ngày & mã suất diễn tính theo giờ máy) ---------- */
const offsetMinutes = -new Date(2026, 10, 15, 12, 0).getTimezoneOffset()
if (offsetMinutes !== 420) {
  console.error(
    `Múi giờ hiện tại lệch ${offsetMinutes / 60}h so với UTC. Hãy chạy với TZ=Asia/Ho_Chi_Minh, ví dụ:\n` +
      '  TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs',
  )
  process.exit(1)
}
if (process.argv.includes('--check-only')) process.exit(0)

const { events, slugify } = await import('./legacy/lib/events.js')
const { presoldZone, isSeatPresold } = await import('./legacy/lib/seating.js')
const { ZONE_MAPS, getSeatMap } = await import('./legacy/data/venueMaps.js')
const { categories } = await import('./legacy/data/navigation.js')
const { heroBanners } = await import('./legacy/data/hero.js')
const { featuredEvents, trendingEvents, posters, resaleTickets } = await import('./legacy/data/home.js')
const { catalog, schedules } = await import('./legacy/data/discover.js')
const { COUPONS } = await import('./legacy/data/rules.js')
const { normalizeVi } = await import('./legacy/lib/utils.js')

/** Thẻ khác tên nhưng là cùng một sự kiện → slug chuẩn */
const ALIASES = { 'concert-dem-4-tinh-ha': 'concert-dem-4-hen-giua-tinh-ha' }

const pad = (n) => String(n).padStart(2, '0')
/** Date (giờ máy = giờ VN) → "YYYY-MM-DDTHH:mm:00+07:00" */
const isoVN = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00+07:00`
const ddMM = (d) => `${pad(d.getDate())}.${pad(d.getMonth() + 1)}`

/* ---------- 2. Sơ đồ ---------- */
const maps = Object.entries(ZONE_MAPS).map(([id, m]) => {
  const { name, viewBox, groups, zones, ...display } = m
  return {
    id,
    kind: 'zones',
    name,
    viewBox,
    display,
    groups: Object.entries(groups).map(([gid, g]) => ({ id: gid, label: g.label, color: g.color, ink: !!g.ink, maxPerOrder: g.max ?? null, perks: g.perks || '' })),
    zones: zones.map((z) => ({ id: z.id, label: z.label, groupId: z.group, capacity: z.cap, shape: z.shape, text: z.text || [z.label] })),
    seats: [],
  }
})
const seatMapIds = [...new Set(events.filter((e) => e.layout === 'seats').map((e) => e.map))]
for (const id of seatMapIds) {
  const m = getSeatMap(id)
  // Bỏ các trường là hàm / dữ liệu dựng ghế, giữ phần hiển thị
  const { name, groups, seats, sections, groupOf, id: _id, ...rest } = m
  const display = Object.fromEntries(Object.entries(rest).filter(([, v]) => typeof v !== 'function'))
  maps.push({
    id,
    kind: 'seats',
    name,
    viewBox: null,
    display,
    groups: Object.entries(groups).map(([gid, g]) => ({ id: gid, label: g.label, color: g.color, ink: !!g.ink, maxPerOrder: g.max ?? null, perks: g.perks || '' })),
    zones: [],
    seats: seats.map((s) => ({ id: s.id, section: s.section, row: s.row, num: s.num, groupId: s.group, label: s.label, x: s.x, y: s.y })),
  })
}

/* ---------- 3. Sự kiện ---------- */
const outEvents = events
  .filter((e) => !ALIASES[e.slug])
  .map((e) => {
    const shows = e.shows.map((s) => ({ id: s.id, startsAt: isoVN(s.start), endTime: s.endTime }))
    const tiers = e.tiers.map((t, i) => ({
      id: t.id,
      name: t.name,
      price: t.price,
      capacity: e.layout === 'list' ? t.remaining : t.capacity,
      maxPerOrder: t.max,
      perks: t.perks || '',
      groupId: t.group ?? null,
      sortOrder: i + 1,
    }))
    const presold = []
    const presoldSeats = []
    for (const s of e.shows) {
      if (e.layout === 'zones') {
        for (const t of e.tiers) presold.push({ showId: s.id, tierId: t.id, qty: presoldZone(e.slug, s.id, t.id, t.capacity) })
      } else if (e.layout === 'seats') {
        for (const seat of getSeatMap(e.map).seats) if (isSeatPresold(e.slug, s.id, seat.id)) presoldSeats.push({ showId: s.id, seatId: seat.id })
      }
    }
    return {
      slug: e.slug,
      title: e.title,
      searchText: normalizeVi(`${e.title} ${e.city} ${e.venue} ${e.categoryLabel}`),
      categoryId: e.category,
      city: e.city,
      venue: e.venue,
      address: e.address,
      layout: e.layout,
      mapId: e.layout === 'list' ? null : e.map,
      hostName: e.organizer?.name ?? null,
      hostBio: e.organizer?.bio ?? null,
      description: e.description,
      notes: e.notes,
      saleStart: e.status === 'coming' ? isoVN(e.saleOpensAt) : null,
      resaleCount: e.resaleCount || 0,
      shows,
      tiers,
      presold,
      presoldSeats,
    }
  })
const bySlug = new Map(outEvents.map((e) => [e.slug, e]))
const fullBySlug = new Map(events.map((e) => [e.slug, e]))

/* ---------- 4. Vị trí trên trang chủ (meta = chỉ phần trang trí) ---------- */
const parseCardDate = (str = '') => {
  let m = str.match(/(\d{1,2})\.(\d{1,2})/)
  if (m) return `${pad(+m[1])}.${pad(+m[2])}`
  m = str.match(/(\d{1,2})\s*Th\s*(\d{1,2})/i)
  if (m) return `${pad(+m[1])}.${pad(+m[2])}`
  if (str === 'T7') return '07.11'
  if (str === 'CN') return '08.11'
  return null
}

const SOURCES = [
  ['hero', heroBanners, (b) => ({ no: b.no }), (b) => ({ date: parseCardDate(`${b.day} Th ${b.month.replace(/\D/g, '')}`), time: b.time })],
  ['featured-upcoming', featuredEvents.upcoming, () => ({}), (c) => ({ date: parseCardDate(c.date), time: c.time })],
  ['featured-new', featuredEvents.new, () => ({}), (c) => ({ date: parseCardDate(c.date), time: c.time })],
  ['trending', trendingEvents, (c) => ({ rank: c.rank, num: c.num }), (c) => ({ date: parseCardDate(c.date) })],
  ['posters', posters, (c) => ({ tag: c.tag, tilt: c.tilt }), (c) => ({ date: parseCardDate(c.date) })],
  ['resale', resaleTickets, (c) => ({ line: c.line }), (c) => ({ date: parseCardDate(c.meta.split(' · ')[1]) })],
  ['schedule-weekend', schedules.weekend.items, () => ({}), (c) => ({ date: parseCardDate(c.day), time: c.time, price: c.price })],
  ['schedule-month', schedules.month.items, () => ({}), (c) => ({ date: parseCardDate(c.day), time: c.time, price: c.price })],
  ['catalog', catalog, (c) => ({ cityId: c.cityId }), (c) => ({ date: parseCardDate(c.date), price: c.price })],
]

const homeSlots = []
const changes = []
for (const [section, items, metaOf, shownOf] of SOURCES) {
  items.forEach((card, i) => {
    const raw = slugify(card.title)
    const slug = ALIASES[raw] ?? raw
    const ev = bySlug.get(slug)
    if (!ev) throw new Error(`Thẻ "${card.title}" (${section}) không khớp sự kiện nào`)
    homeSlots.push({ section, position: i + 1, slug, meta: metaOf(card) })

    const full = fullBySlug.get(slug)
    const first = full.shows[0]
    const shown = shownOf(card)
    const diffs = []
    if (raw !== slug) diffs.push(`gộp "${card.title}" → "${full.title}"`)
    if (shown.date && shown.date !== ddMM(first.start)) diffs.push(`ngày ${shown.date} → ${ddMM(first.start)}`)
    if (shown.time && shown.time !== first.startTime) diffs.push(`giờ ${shown.time} → ${first.startTime}`)
    if (shown.price && shown.price !== full.minPrice / 1000) diffs.push(`giá ${shown.price}k → ${full.minPrice / 1000}k`)
    if (diffs.length) changes.push(`[${section} #${i + 1}] ${card.title}: ${diffs.join('; ')}`)
  })
}

/* ---------- 5. Ghi file + báo cáo ---------- */
const out = {
  version: 1,
  generatedAt: new Date().toISOString(),
  categories: categories.map((c, i) => ({ id: c.id, label: c.label, dot: c.dot || '', sortOrder: i + 1 })),
  maps,
  events: outEvents,
  homeSlots,
  coupons: Object.entries(COUPONS).map(([code, c]) => ({ code, amount: c.amount, minOrder: c.minOrder })),
}
const file = join(dirname(fileURLToPath(import.meta.url)), 'catalog.json')
writeFileSync(file, `${JSON.stringify(out, null, 2)}\n`, 'utf8')

console.log(`Đã ghi ${file}`)
console.log(`  ${out.categories.length} danh mục · ${maps.length} sơ đồ · ${outEvents.length} sự kiện · ${homeSlots.length} vị trí trang chủ`)
console.log(`\nThẻ thay đổi so với hiện tại (${changes.length}):`)
for (const c of changes) console.log(`  - ${c}`)
