/* Dữ liệu mẫu — thay bằng API thật sau này */

/** Phần 3 · Sắp mở bán / Mới mở bán */
export const featuredEvents = {
  upcoming: [
    { id: 'u1', status: 'SẮP MỞ BÁN', date: '02.01.2027', time: '19:30', title: 'Đêm nhạc “Mười Năm Nhìn Lại”', venue: 'Nhà hát [ĐỊA ĐIỂM], TP.HCM' },
    { id: 'u2', status: 'SẮP MỞ BÁN', date: '18.12.2026', time: '20:00', title: 'Song Phụng — Live in Saigon', venue: 'Sân khấu [ĐỊA ĐIỂM]' },
    { id: 'u3', status: 'SẮP MỞ BÁN', date: '24.12.2026', time: '19:00', title: 'Nhạc kịch “Phố Đèn Lồng”', venue: 'Nhà hát [ĐỊA ĐIỂM], Hà Nội' },
    { id: 'u4', status: 'SẮP MỞ BÁN', date: '31.12.2026', time: '21:00', title: 'Countdown Bờ Sông 2027', venue: 'Quảng trường [ĐỊA ĐIỂM]' },
  ],
  new: [
    { id: 'n1', status: 'MỚI MỞ BÁN', date: '22.11.2026', time: '19:00', title: 'Fanmeeting “Về Nhà”', venue: 'Nhà hát [ĐỊA ĐIỂM], TP.HCM' },
    { id: 'n2', status: 'MỚI MỞ BÁN', date: '05.12.2026', time: '19:30', title: 'Concert Anh Em Vượt Núi', venue: 'Sân vận động [ĐỊA ĐIỂM], Hà Nội' },
    { id: 'n3', status: 'MỚI MỞ BÁN', date: '13.12.2026', time: '20:00', title: 'Dạ Quang — Live Show', venue: 'Sân khấu [ĐỊA ĐIỂM], Đà Lạt' },
    { id: 'n4', status: 'MỚI MỞ BÁN', date: '20.12.2026', time: '19:30', title: 'Ánh Kim — Reunion', venue: 'Nhà hát [ĐỊA ĐIỂM], Hà Nội' },
  ],
}

/** Phần 3 · Đang lên nhịp — num: màu số hạng */
export const trendingEvents = [
  { id: 't1', rank: 1, date: '05.12', title: 'Concert Anh Em Vượt Núi', num: 'text-mustard' },
  { id: 't2', rank: 2, date: '22.11', title: 'Fanmeeting “Về Nhà”', num: 'text-paper' },
  { id: 't3', rank: 3, date: '29.11', title: 'Lễ hội Âm nhạc Thành Phố', num: 'text-cobalt' },
  { id: 't4', rank: 4, date: '15.11', title: 'Concert Đêm 4: Tinh Hà', num: 'text-tomato' },
]

/** Phần 4 · Huy hiệu ngôi sao */
export const stars = [
  { id: 's1', initials: 'GB', name: 'Nhóm Gió Bấc', bg: 'bg-tomato', fg: 'text-cream', ring: 'border-mustard' },
  { id: 's2', initials: 'LN', name: 'Lam Ngọc', bg: 'bg-mustard', fg: 'text-ink', ring: 'border-ink' },
  { id: 's3', initials: 'SM', name: 'Sân khấu Mộc', bg: 'bg-cobalt', fg: 'text-cream', ring: 'border-cream' },
  { id: 's4', initials: 'ĐĐ', name: 'Đêm Đỏ Live', bg: 'bg-ink', fg: 'text-cream', ring: 'border-tomato' },
  { id: 's5', initials: 'AK', name: 'An Khuê', bg: 'bg-paper', fg: 'text-ink', ring: 'border-tomato' },
  { id: 's6', initials: 'TÂ', name: 'Trạm Âm Thanh', bg: 'bg-forest', fg: 'text-cream', ring: 'border-cream' },
  { id: 's7', initials: 'ML', name: 'Mây Lang Thang', bg: 'bg-blush', fg: 'text-ink', ring: 'border-ink' },
  { id: 's8', initials: 'HK', name: 'Hội Kịch Trẻ', bg: 'bg-mustard', fg: 'text-ink', ring: 'border-ink' },
]

/** Phần 4 · Bảng dán poster */
export const posters = [
  { id: 'p1', title: 'Ai Chồng Ai', tag: 'HÀI KỊCH', date: '28.11', tilt: '-rotate-2' },
  { id: 'p2', title: 'Hừng Đông', tag: 'CONCERT', date: '06.12', tilt: 'rotate-1' },
  { id: 'p3', title: 'Dạ Quang', tag: 'LIVE SHOW', date: '13.12', tilt: '-rotate-1' },
  { id: 'p4', title: 'Thành Phố Mở Màng', tag: 'YEAR END', date: '12.12', tilt: 'rotate-2' },
  { id: 'p5', title: 'Ánh Kim', tag: 'REUNION', date: '20.12', tilt: '-rotate-1' },
  { id: 'p6', title: 'Gánh Hát Rong', tag: 'CẢI LƯƠNG', date: '27.12', tilt: 'rotate-1' },
  { id: 'p7', title: 'Mưa Tháng Sáu', tag: 'ACOUSTIC', date: '03.01', tilt: '-rotate-2' },
]

/** Phần 5 · Chợ vé sang tay — line: màu đường chấm */
export const resaleTickets = [
  { id: 'r1', title: 'Live Concert “Vũ Trụ Đỏ” 2026', meta: 'Hà Nội · 12 Th 12', count: 14, line: 'border-tomato' },
  { id: 'r2', title: 'Kịch: Tấm Cám Đại Chiến', meta: 'TP.HCM · 12 Th 11', count: 6, line: 'border-forest' },
  { id: 'r3', title: 'Kịch: Một Ngày Làm Vua', meta: 'TP.HCM · 20 Th 11', count: 9, line: 'border-cobalt' },
]

/** Phần 6 · Thẻ thành viên */
export const memberPasses = [
  { id: 'm1', name: 'Trạm Âm Thanh', no: '0412', type: 'OFFICIAL CLUB', price: 334800, bg: 'bg-forest', arc: 'bg-mustard' },
  { id: 'm2', name: 'Lam Ngọc Fanclub', no: '0087', type: 'FAN PASS', price: 247000, bg: 'bg-cobalt', arc: 'bg-violet' },
  { id: 'm3', name: 'Thiên Nga Đen', no: '1990', type: 'SWAN PASS', price: 324000, bg: 'bg-ink', arc: 'bg-tomato', soldOut: true },
]

export const couponPartners = ['[NGÂN HÀNG 1]', '[NGÂN HÀNG 2]', '[NGÂN HÀNG 3]', '[VÍ ĐIỆN TỬ 1]', '[VÍ ĐIỆN TỬ 2]', '+18 đối tác']
