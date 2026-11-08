/* ==========================================================================
   SƠ ĐỒ ĐỊA ĐIỂM — dùng chung cho giao diện và máy chủ (chỉ import tương đối)

   1. ZONE_MAPS: sơ đồ khu vực (concert, fanmeeting) — mỗi khu là một hạng vé
      shape: { type: 'rect', x, y, w, h } | { type: 'poly', points }
      text : các dòng chữ hiển thị trong khu (mặc định = label)
      cap  : sức chứa của khu
   2. SEAT_MAPS: sơ đồ ghế ngồi (nhà hát) — sinh ghế tự động từ các khối ghế
   ========================================================================== */

/* ---------------------------------------------------------------------------
   SƠ ĐỒ KHU VỰC
--------------------------------------------------------------------------- */
export const ZONE_MAPS = {
  /* Sân khấu lớn: sân khấu chính + runway + B-stage, fanzone, GA, CAT, VIP, Sky lounge */
  arena: {
    name: 'Sân khấu Arena',
    viewBox: '0 0 1000 680',
    groups: {
      sky: { label: 'SKY LOUNGE', color: '#8be4f7', ink: true, max: 2, perks: 'Khu lounge riêng, ghế sofa, đồ uống miễn phí, lối đi riêng.' },
      svip: { label: 'SVIP', color: '#4fc3e8', ink: true, max: 4, perks: 'Ghế ngồi trung tâm phía sau B-stage, quà tặng độc quyền.' },
      vip: { label: 'VIP', color: '#2a86a8', max: 4, perks: 'Ghế ngồi gần B-stage, check-in sớm.' },
      fanzone: { label: 'FANZONE', color: '#8b5cf6', max: 4, perks: 'Khu đứng sát sân khấu chính và runway.' },
      ga1: { label: 'GA 1', color: '#e879f9', ink: true, max: 6, perks: 'Khu đứng hai bên fanzone.' },
      ga2: { label: 'GA 2', color: '#f0abfc', ink: true, max: 6, perks: 'Khu đứng phía ngoài.' },
      cat1: { label: 'CAT 1', color: '#a855f7', max: 6, perks: 'Ghế ngồi khán đài phía sau, nhìn thẳng sân khấu.' },
      cat2: { label: 'CAT 2', color: '#6d3fc4', max: 6, perks: 'Ghế ngồi khán đài hai bên.' },
      cat3: { label: 'CAT 3', color: '#c026d3', max: 6, perks: 'Ghế ngồi khán đài góc.' },
    },
    decor: [
      { kind: 'stage', text: ['STAGE'], fs: 40, shape: { type: 'poly', points: '330,30 670,30 670,100 580,100 580,150 420,150 420,100 330,100' }, lx: 500, ly: 88 },
      { kind: 'screen', text: ['LED'], fs: 14, shape: { type: 'rect', x: 205, y: 45, w: 85, h: 40 } },
      { kind: 'screen', text: ['LED'], fs: 14, shape: { type: 'rect', x: 710, y: 45, w: 85, h: 40 } },
      { kind: 'stage', text: [], shape: { type: 'rect', x: 488, y: 150, w: 24, h: 250 } },
      { kind: 'stage', text: ['B-STAGE'], fs: 22, shape: { type: 'rect', x: 380, y: 400, w: 240, h: 44 } },
      { kind: 'foh', text: ['FOH'], fs: 18, shape: { type: 'rect', x: 455, y: 585, w: 90, h: 50 } },
    ],
    zones: [
      { id: 'fanzone-a', label: 'FANZONE A', group: 'fanzone', cap: 600, text: ['FANZONE', 'A'], shape: { type: 'rect', x: 330, y: 180, w: 145, h: 200 } },
      { id: 'fanzone-b', label: 'FANZONE B', group: 'fanzone', cap: 600, text: ['FANZONE', 'B'], shape: { type: 'rect', x: 525, y: 180, w: 145, h: 200 } },
      { id: 'ga-1a', label: 'GA 1A', group: 'ga1', cap: 900, text: ['GA', '1A'], shape: { type: 'rect', x: 230, y: 170, w: 85, h: 280 } },
      { id: 'ga-1b', label: 'GA 1B', group: 'ga1', cap: 900, text: ['GA', '1B'], shape: { type: 'rect', x: 685, y: 170, w: 85, h: 280 } },
      { id: 'ga-2a', label: 'GA 2A', group: 'ga2', cap: 800, text: ['GA', '2A'], shape: { type: 'rect', x: 135, y: 170, w: 80, h: 280 } },
      { id: 'ga-2b', label: 'GA 2B', group: 'ga2', cap: 800, text: ['GA', '2B'], shape: { type: 'rect', x: 785, y: 170, w: 80, h: 280 } },
      { id: 'cat-3a', label: 'CAT 3A', group: 'cat3', cap: 400, text: ['CAT', '3A'], shape: { type: 'rect', x: 20, y: 170, w: 100, h: 110 } },
      { id: 'cat-3b', label: 'CAT 3B', group: 'cat3', cap: 400, text: ['CAT', '3B'], shape: { type: 'rect', x: 880, y: 170, w: 100, h: 110 } },
      { id: 'cat-2a', label: 'CAT 2A', group: 'cat2', cap: 700, text: ['CAT', '2A'], shape: { type: 'rect', x: 20, y: 295, w: 100, h: 240 } },
      { id: 'cat-2b', label: 'CAT 2B', group: 'cat2', cap: 700, text: ['CAT', '2B'], shape: { type: 'rect', x: 880, y: 295, w: 100, h: 240 } },
      { id: 'vip-a', label: 'VIP A', group: 'vip', cap: 250, text: ['VIP A'], shape: { type: 'rect', x: 230, y: 470, w: 110, h: 70 } },
      { id: 'vip-b', label: 'VIP B', group: 'vip', cap: 250, text: ['VIP B'], shape: { type: 'rect', x: 660, y: 470, w: 110, h: 70 } },
      { id: 'svip-a', label: 'SVIP A', group: 'svip', cap: 120, text: ['SVIP', 'A'], shape: { type: 'rect', x: 350, y: 470, w: 80, h: 70 } },
      { id: 'svip-b', label: 'SVIP B', group: 'svip', cap: 120, text: ['SVIP', 'B'], shape: { type: 'rect', x: 570, y: 470, w: 80, h: 70 } },
      { id: 'sky', label: 'SKY LOUNGE', group: 'sky', cap: 60, text: ['SKY', 'LOUNGE'], shape: { type: 'rect', x: 440, y: 460, w: 120, h: 95 } },
      { id: 'cat-1a', label: 'CAT 1A', group: 'cat1', cap: 1200, text: ['CAT 1A'], shape: { type: 'rect', x: 130, y: 570, w: 300, h: 85 } },
      { id: 'cat-1b', label: 'CAT 1B', group: 'cat1', cap: 1200, text: ['CAT 1B'], shape: { type: 'rect', x: 570, y: 570, w: 300, h: 85 } },
    ],
  },

  /* Hội trường: sân khấu bán nguyệt, lưới 5 cột × 4 hạng */
  'hall-grid': {
    name: 'Hội trường',
    viewBox: '0 0 580 560',
    groups: {
      svip: { label: 'SVIP', color: '#f5ec7a', ink: true, max: 4, perks: 'Hàng đầu sát sân khấu, giao lưu cùng nghệ sĩ.' },
      vip: { label: 'VIP', color: '#3b7dd8', max: 4, perks: 'Vị trí gần sân khấu, quà lưu niệm.' },
      a: { label: 'KHU A', color: '#f07a7a', ink: true, max: 6, perks: 'Khu giữa hội trường, tầm nhìn tốt.' },
      b: { label: 'KHU B', color: '#d27fca', ink: true, max: 6, perks: 'Khu phía sau, giá tốt.' },
    },
    decor: [
      { kind: 'stage', text: ['STAGE'], fs: 30, shape: { type: 'path', d: 'M190 30 L390 30 A100 80 0 0 1 190 30 Z' }, lx: 290, ly: 72 },
    ],
    zones: (() => {
      const cols = [
        { n: 1, x: 110, w: 70 },
        { n: 2, x: 190, w: 70 },
        { n: 3, x: 270, w: 40 },
        { n: 4, x: 320, w: 70 },
        { n: 5, x: 400, w: 70 },
      ]
      const rows = [
        { g: 'svip', name: 'SVIP', y: 135, h: 110, cap: 60 },
        { g: 'vip', name: 'VIP', y: 255, h: 70, cap: 80 },
        { g: 'a', name: 'KHU A', y: 335, h: 110, cap: 140 },
        { g: 'b', name: 'KHU B', y: 455, h: 60, cap: 100 },
      ]
      return rows.flatMap((r) =>
        cols.map((c) => ({
          id: `${r.g}-${c.n}`,
          label: `${r.name}-${c.n}`,
          group: r.g,
          cap: c.w < 50 ? Math.round(r.cap / 2) : r.cap,
          text: c.w < 50 ? [String(c.n)] : [r.name, String(c.n)],
          fs: c.w < 50 ? 14 : 15,
          shape: { type: 'rect', x: c.x, y: r.g === 'svip' && (c.n === 1 || c.n === 5) ? r.y - 20 : r.y, w: c.w, h: r.g === 'svip' && (c.n === 1 || c.n === 5) ? r.h + 20 : r.h },
        })),
      )
    })(),
  },

  /* Nhà hát 2 tầng, các "tổ" hình thang */
  'theatre-tiers': {
    name: 'Nhà hát 2 tầng',
    viewBox: '0 0 800 640',
    groups: {
      to1: { label: 'TỔ 1', color: '#ef5b4b', max: 2, perks: 'Ba hàng ghế đầu tầng 1, tham gia ký tặng và chụp ảnh nhóm.' },
      to2: { label: 'TỔ 2', color: '#2fa36b', max: 4, perks: 'Ghế ngồi tầng 1, poster có chữ ký in.' },
      to3: { label: 'TỔ 3', color: '#7559f0', max: 4, perks: 'Ghế ngồi tầng 1 phía sau và tầng 2 phía trước.' },
      to4: { label: 'TỔ 4', color: '#f5a524', ink: true, max: 6, perks: 'Ghế ngồi tầng 2, nhận lightstick phiên bản đặc biệt.' },
    },
    decor: [
      { kind: 'stage', text: ['STAGE'], fs: 30, shape: { type: 'rect', x: 230, y: 15, w: 340, h: 48 } },
      { kind: 'label', text: ['TẦNG 1'], fs: 30, lx: 400, ly: 108 },
      { kind: 'foh', text: ['FOH'], fs: 16, shape: { type: 'rect', x: 350, y: 318, w: 100, h: 30 } },
      { kind: 'label', text: ['TẦNG 2'], fs: 30, lx: 400, ly: 410 },
    ],
    zones: [
      { id: 'to1', label: 'Tổ 1', group: 'to1', cap: 90, text: ['TỔ 1'], shape: { type: 'poly', points: '300,130 500,130 520,240 280,240' } },
      { id: 'to2-trai', label: 'Tổ 2 · Trái', group: 'to2', cap: 110, text: ['TỔ 2'], shape: { type: 'poly', points: '110,130 260,130 260,240 130,240' } },
      { id: 'to2-phai', label: 'Tổ 2 · Phải', group: 'to2', cap: 110, text: ['TỔ 2'], shape: { type: 'poly', points: '540,130 690,130 670,240 540,240' } },
      { id: 'to2-giua', label: 'Tổ 2 · Giữa', group: 'to2', cap: 120, text: ['TỔ 2'], shape: { type: 'poly', points: '280,252 520,252 520,318 450,318 450,305 350,305 350,318 280,318' }, ly: 285 },
      { id: 'to3-trai', label: 'Tổ 3 · Trái', group: 'to3', cap: 90, text: ['TỔ 3'], shape: { type: 'poly', points: '140,252 260,252 260,330 155,330' } },
      { id: 'to3-phai', label: 'Tổ 3 · Phải', group: 'to3', cap: 90, text: ['TỔ 3'], shape: { type: 'poly', points: '540,252 660,252 645,330 540,330' } },
      { id: 'to3-t2-trai', label: 'Tổ 3 · Tầng 2 trái', group: 'to3', cap: 50, text: ['TỔ 3'], fs: 14, shape: { type: 'poly', points: '150,380 225,380 230,440 145,440' } },
      { id: 'to3-t2-phai', label: 'Tổ 3 · Tầng 2 phải', group: 'to3', cap: 50, text: ['TỔ 3'], fs: 14, shape: { type: 'poly', points: '575,380 650,380 655,440 570,440' } },
      { id: 'to3-hang-trai', label: 'Tổ 3 · Hàng trái', group: 'to3', cap: 80, text: ['TỔ 3'], shape: { type: 'poly', points: '100,455 260,455 260,500 80,500' } },
      { id: 'to3-hang-giua', label: 'Tổ 3 · Hàng giữa', group: 'to3', cap: 90, text: ['TỔ 3'], shape: { type: 'rect', x: 285, y: 460, w: 230, h: 40 } },
      { id: 'to3-hang-phai', label: 'Tổ 3 · Hàng phải', group: 'to3', cap: 80, text: ['TỔ 3'], shape: { type: 'poly', points: '540,455 700,455 720,500 540,500' } },
      { id: 'to4-trai', label: 'Tổ 4 · Trái', group: 'to4', cap: 160, text: ['TỔ 4'], shape: { type: 'poly', points: '75,512 260,512 260,600 105,600' } },
      { id: 'to4-giua', label: 'Tổ 4 · Giữa', group: 'to4', cap: 180, text: ['TỔ 4'], shape: { type: 'poly', points: '275,512 335,512 335,545 465,545 465,512 525,512 535,600 265,600' }, ly: 578 },
      { id: 'to4-phai', label: 'Tổ 4 · Phải', group: 'to4', cap: 160, text: ['TỔ 4'], shape: { type: 'poly', points: '540,512 725,512 695,600 540,600' } },
    ],
  },
}

/* ---------------------------------------------------------------------------
   SƠ ĐỒ GHẾ NGỒI
   sections: các khối ghế; seats(rowIndex) = số ghế của hàng; align: căn ghế trong khối
   groupOf(row, sectionId) → hạng ghế
--------------------------------------------------------------------------- */
const letters = (s) => s.split('')

const SEAT_DEFS = {
  /* Nhà hát lớn: 3 khối + ban công */
  'nha-hat-lon': {
    name: 'Nhà hát lớn',
    width: 935,
    height: 580,
    pitch: 26,
    radius: 9,
    stage: { x: 236, y: 18, w: 460, h: 50, text: 'SÂN KHẤU' },
    groups: {
      diamond: { label: 'DIAMOND', color: '#c084fc', perks: 'Ba hàng đầu khu giữa, gần sân khấu nhất.' },
      gold: { label: 'GOLD', color: '#f2b705', perks: 'Khu giữa hàng D–F và hai khu bên hàng A–F.' },
      silver: { label: 'SILVER', color: '#7cc4f2', perks: 'Hàng G–I, tầm nhìn bao quát.' },
      bronze: { label: 'BRONZE', color: '#e9a8c8', perks: 'Hàng J–L và ban công.' },
    },
    sections: [
      { id: 'T', label: 'Khu trái', x: 40, y: 110, rows: letters('ABCDEFGHIJKL'), maxSeats: 7, seats: (i) => (i < 2 ? 5 : 7), align: 'right', labelSides: ['left'] },
      { id: 'G', label: 'Khu giữa', x: 270, y: 110, rows: letters('ABCDEFGHIJKL'), maxSeats: 16, seats: (i) => (i === 0 ? 12 : i === 1 ? 14 : 16), align: 'center' },
      { id: 'P', label: 'Khu phải', x: 736, y: 110, rows: letters('ABCDEFGHIJKL'), maxSeats: 7, seats: (i) => (i < 2 ? 5 : 7), align: 'left', labelSides: ['right'] },
      { id: 'B', label: 'Ban công', x: 128, y: 460, rows: letters('MNOP'), maxSeats: 26, seats: () => 26, aisleAfter: 13, align: 'left' },
    ],
    groupOf(row, sec) {
      if (sec === 'B') return 'bronze'
      const i = 'ABCDEFGHIJKL'.indexOf(row)
      if (sec === 'G') return i < 3 ? 'diamond' : i < 6 ? 'gold' : i < 9 ? 'silver' : 'bronze'
      return i < 6 ? 'gold' : i < 9 ? 'silver' : 'bronze'
    },
    labels: [{ text: 'BAN CÔNG', x: 466, y: 445 }],
  },

  /* Sân khấu kịch nhỏ: 1 khối, lối đi giữa */
  'san-khau-nho': {
    name: 'Sân khấu kịch',
    width: 512,
    height: 380,
    pitch: 28,
    radius: 10,
    stage: { x: 76, y: 18, w: 360, h: 46, text: 'SÂN KHẤU' },
    groups: {
      vip: { label: 'VIP', color: '#f2b705', perks: 'Ba hàng đầu, gần sân khấu.' },
      thuong: { label: 'VÉ THƯỜNG', color: '#7cc4f2', perks: 'Hàng D–I.' },
    },
    sections: [{ id: 'S', label: 'Khán phòng', x: 60, y: 110, rows: letters('ABCDEFGHI'), maxSeats: 14, seats: (i) => (i === 0 ? 12 : 14), aisleAfter: 7, align: 'center' }],
    groupOf: (row) => ('ABC'.includes(row) ? 'vip' : 'thuong'),
    labels: [],
  },
}

const seatCache = new Map()

/** Sinh danh sách ghế (có toạ độ) cho một sơ đồ ghế — có cache */
export function getSeatMap(id) {
  if (seatCache.has(id)) return seatCache.get(id)
  const def = SEAT_DEFS[id]
  if (!def) return null
  const seats = []
  const rowLabels = []
  for (const sec of def.sections) {
    sec.rows.forEach((row, ri) => {
      const n = sec.seats(ri)
      const y = sec.y + ri * def.pitch
      const offset = sec.align === 'right' ? sec.maxSeats - n : sec.align === 'center' ? (sec.maxSeats - n) / 2 : 0
      let minX = Infinity
      let maxX = -Infinity
      for (let i = 0; i < n; i++) {
        let x = sec.x + (offset + i) * def.pitch
        if (sec.aisleAfter && i + offset >= sec.aisleAfter) x += def.pitch
        minX = Math.min(minX, x)
        maxX = Math.max(maxX, x)
        const num = i + 1
        seats.push({
          id: `${sec.id}-${row}${num}`,
          x,
          y,
          row,
          num,
          section: sec.id,
          group: def.groupOf(row, sec.id),
          label: `${sec.label} · Hàng ${row} · Ghế ${num}`,
        })
      }
      const sides = sec.labelSides || ['left', 'right']
      if (sides.includes('left')) rowLabels.push({ text: row, x: minX - def.pitch * 0.85, y })
      if (sides.includes('right')) rowLabels.push({ text: row, x: maxX + def.pitch * 0.85, y })
    })
  }
  const map = { ...def, id, seats, rowLabels }
  seatCache.set(id, map)
  return map
}
