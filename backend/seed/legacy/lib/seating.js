/* ==========================================================================
   LOGIC CHỖ NGỒI — dùng chung cho giao diện và máy chủ (chỉ import tương đối)
   "Đã bán sẵn" (presold) mô phỏng lượng vé đã bán trước khi hệ thống chạy,
   tính bằng hàm băm cố định nên máy chủ và giao diện luôn ra cùng kết quả.
   Vé bán qua hệ thống được máy chủ trừ thêm từ cơ sở dữ liệu.
   ========================================================================== */
import { getSeatMap } from '../data/venueMaps.js'

export const hashStr = (s) => {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}
const frac = (key) => (hashStr(key) % 10000) / 10000

/** Số chỗ đã bán sẵn của một khu (sơ đồ khu vực). ~12% khu đã hết vé */
export function presoldZone(slug, showId, zoneId, cap) {
  const f = frac(`${slug}|${showId}|${zoneId}`)
  if (f < 0.12) return cap
  return Math.floor(cap * f * 0.85)
}

/** Ghế đã bán sẵn? Tỉ lệ 25–60% tuỳ suất diễn */
export function isSeatPresold(slug, showId, seatId) {
  const rate = 0.25 + frac(`${slug}|${showId}`) * 0.35
  return frac(`${slug}|${showId}|${seatId}`) < rate
}

/** Danh sách ghế của sự kiện bán theo ghế */
export const seatsOf = (event) => (event.layout === 'seats' ? getSeatMap(event.map).seats : [])

/** Map seatId → ghế */
const indexCache = new Map()
export function seatIndex(event) {
  if (!indexCache.has(event.map)) indexCache.set(event.map, new Map(seatsOf(event).map((s) => [s.id, s])))
  return indexCache.get(event.map)
}

/** Số vé còn lại TRƯỚC khi trừ vé bán qua hệ thống */
export function baseRemaining(event, showId, tier) {
  if (event.layout === 'zones') return tier.capacity - presoldZone(event.slug, showId, tier.id, tier.capacity)
  if (event.layout === 'seats') {
    return seatsOf(event).filter((s) => s.group === tier.id && !isSeatPresold(event.slug, showId, s.id)).length
  }
  return tier.remaining
}
