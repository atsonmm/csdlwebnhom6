/* Xuất sự kiện như giao diện JS cũ đang thấy (backend/seed/legacy/lib/events.js — bản chụp dữ liệu JS cũ) → backend/tests/fixtures/legacy_events.json
   Dùng để test API /api/events/{slug} trả về đúng dữ liệu cũ.
     TZ=Asia/Ho_Chi_Minh node backend/seed/dump_legacy_events.mjs */
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

if (-new Date(2026, 10, 15, 12, 0).getTimezoneOffset() !== 420) {
  console.error('Hãy chạy với TZ=Asia/Ho_Chi_Minh')
  process.exit(1)
}
const { events } = await import('./legacy/lib/events.js')

const ALIASES = new Set(['concert-dem-4-tinh-ha'])
const pad = (n) => String(n).padStart(2, '0')
const isoVN = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00+07:00`

const out = events
  .filter((e) => !ALIASES.has(e.slug))
  .map((e) => ({
    slug: e.slug,
    title: e.title,
    category: e.category,
    categoryLabel: e.categoryLabel,
    marker: e.marker,
    city: e.city,
    venue: e.venue,
    address: e.address,
    layout: e.layout,
    map: e.layout === 'list' ? null : e.map,
    status: e.status,
    // JS cũ gán saleOpensAt mặc định cho MỌI sự kiện; chỉ có nghĩa khi status = 'coming'
    saleOpensAt: e.status === 'coming' ? isoVN(e.saleOpensAt) : null,
    start: isoVN(e.start),
    startTime: e.startTime,
    endTime: e.endTime,
    minPrice: e.minPrice,
    organizer: { name: e.organizer.name, bio: e.organizer.bio },
    description: e.description,
    notes: e.notes,
    resaleCount: e.resaleCount || 0,
    shows: e.shows.map((s) => ({ id: s.id, start: isoVN(s.start), startTime: s.startTime, endTime: s.endTime })),
    tiers: e.tiers.map((t) => ({
      id: t.id,
      name: t.name,
      price: t.price,
      perks: t.perks || '',
      max: t.max,
      group: t.group ?? null,
      groupLabel: t.groupLabel ?? null,
      color: t.color ?? null,
    })),
  }))

const file = join(dirname(fileURLToPath(import.meta.url)), '../tests/fixtures/legacy_events.json')
writeFileSync(file, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
console.log(`Đã ghi ${out.length} sự kiện → ${file}`)
