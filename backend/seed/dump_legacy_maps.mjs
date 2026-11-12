/* Xuất sơ đồ địa điểm như giao diện JS cũ đang dùng (backend/seed/legacy/data/venueMaps.js — bản chụp dữ liệu JS cũ)
   → backend/tests/fixtures/legacy_maps.json, để test API /api/maps/{id}.
     TZ=Asia/Ho_Chi_Minh node backend/seed/dump_legacy_maps.mjs
   Chuẩn hoá giống export_catalog.mjs: text khu mặc định = [label], ink mặc định false,
   max/perks thiếu → null/''. Bỏ các trường là hàm và dữ liệu dựng ghế (sections, groupOf). */
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const { events } = await import('./legacy/lib/events.js')
const { ZONE_MAPS, getSeatMap } = await import('./legacy/data/venueMaps.js')

const groupsOf = (groups) =>
  Object.fromEntries(
    Object.entries(groups).map(([gid, g]) => [gid, { label: g.label, color: g.color, ink: !!g.ink, max: g.max ?? null, perks: g.perks || '' }]),
  )

const out = []
for (const [id, m] of Object.entries(ZONE_MAPS)) {
  const { name, viewBox, groups, zones, ...display } = m
  out.push({
    id,
    kind: 'zones',
    name,
    viewBox,
    ...display,
    groups: groupsOf(groups),
    zones: zones.map((z) => ({ id: z.id, label: z.label, group: z.group, cap: z.cap, text: z.text || [z.label], shape: z.shape })),
  })
}
for (const id of [...new Set(events.filter((e) => e.layout === 'seats').map((e) => e.map))]) {
  const { name, groups, seats, sections, groupOf, id: _id, ...rest } = getSeatMap(id)
  const display = Object.fromEntries(Object.entries(rest).filter(([, v]) => typeof v !== 'function'))
  out.push({
    id,
    kind: 'seats',
    name,
    ...display,
    groups: groupsOf(groups),
    seats: seats.map((s) => ({ id: s.id, x: s.x, y: s.y, row: s.row, num: s.num, section: s.section, group: s.group, label: s.label })),
  })
}

const file = join(dirname(fileURLToPath(import.meta.url)), '../tests/fixtures/legacy_maps.json')
writeFileSync(file, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
console.log(`Đã ghi ${out.length} sơ đồ → ${file}`)
