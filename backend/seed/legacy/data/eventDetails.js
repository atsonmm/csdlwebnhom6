/* Thông tin chi tiết cho các sự kiện nổi bật.
   Sự kiện không có ở đây sẽ được sinh thông tin mặc định trong src/lib/events.js

   layout: 'zones' — sơ đồ khu vực (map = khoá trong ZONE_MAPS, prices = giá theo nhóm khu)
           'seats' — chọn ghế    (map = khoá trong SEAT_MAPS, prices = giá theo hạng ghế)
           'list'  — chỉ chọn loại vé (mặc định; tiers = danh sách loại vé)
   shows : các suất diễn [{ date: 'YYYY-MM-DD', time: 'HH:MM', endTime: 'HH:MM' }] */

export const eventDetails = [
  /* ---------------- Sơ đồ khu vực ---------------- */
  {
    title: 'Concert Đêm 4: Hẹn Giữa Tinh Hà',
    category: 'nhac-song',
    city: 'Hà Nội',
    venue: 'Trung tâm Triển lãm [ĐỊA ĐIỂM]',
    address: '[ĐỊA CHỈ], Hà Nội',
    time: '19:00',
    endTime: '23:00',
    layout: 'zones',
    map: 'arena',
    prices: { sky: 10000000, svip: 5000000, vip: 4000000, fanzone: 2500000, cat1: 2500000, cat2: 1800000, cat3: 1500000, ga1: 1100000, ga2: 800000 },
    organizer: {
      name: '[BAN TỔ CHỨC]',
      bio: 'Đơn vị tổ chức các chương trình âm nhạc quy mô lớn, mang tới những đêm diễn được dàn dựng công phu về âm thanh, ánh sáng và sân khấu.',
    },
    description: [
      'Sau ba đêm diễn cháy vé, “Hẹn Giữa Tinh Hà” chính thức trở lại với Đêm 4: đêm diễn được mở thêm để dành tặng những khán giả chưa kịp sở hữu tấm vé trong các lần mở bán trước.',
      'Sân khấu chính kết hợp runway và B-stage cùng hệ thống ánh sáng mô phỏng dải ngân hà sẽ đưa khán giả đi qua những bản hit quen thuộc và các tiết mục đặc biệt chỉ có trong đêm diễn này.',
      'Cửa mở từ 17:30. Khán giả nên có mặt sớm để check-in, nhận quà lưu niệm và tham gia các hoạt động bên lề tại khu vực sảnh chờ.',
    ],
  },
  {
    title: 'Concert Anh Em Vượt Núi',
    category: 'nhac-song',
    city: 'Hà Nội',
    venue: 'Sân vận động [ĐỊA ĐIỂM]',
    address: '[ĐỊA CHỈ], Hà Nội',
    time: '19:30',
    endTime: '23:30',
    layout: 'zones',
    map: 'arena',
    prices: { sky: 8000000, svip: 4500000, vip: 3500000, fanzone: 2200000, cat1: 2000000, cat2: 1600000, cat3: 1300000, ga1: 1200000, ga2: 1000000 },
    description: [
      'Đêm nhạc quy tụ dàn nghệ sĩ “anh em” trong một sân khấu quy mô sân vận động. Sau khi hai đêm đầu bán hết, ban tổ chức chính thức công bố thêm đêm 3 và 4.',
      'Khán giả vui lòng mang theo giấy tờ tuỳ thân khi check-in. Mỗi tài khoản được mua tối đa 4 vé cho mỗi khu.',
    ],
  },
  {
    title: 'Fanmeeting “Về Nhà”',
    category: 'nhac-song',
    city: 'TP.HCM',
    venue: 'Nhà hát [ĐỊA ĐIỂM]',
    address: '[ĐỊA CHỈ], TP.HCM',
    time: '19:00',
    endTime: '22:00',
    layout: 'zones',
    map: 'theatre-tiers',
    prices: { to1: 2490000, to2: 1490000, to3: 1099000, to4: 799000 },
    description: [
      'Có những đêm nhạc để nghe, và có những đêm để gặp lại nhau. “Về Nhà” là buổi fanmeeting thân mật với sức chứa giới hạn, nơi khoảng cách giữa sân khấu và khán giả gần hơn bao giờ hết.',
      'Chương trình gồm phần trình diễn acoustic, trò chuyện cùng khán giả, các mini game và phần ký tặng dành riêng cho chủ sở hữu vé Tổ 1.',
    ],
  },
  { title: 'Live Concert XV — 15 năm', layout: 'zones', map: 'hall-grid', time: '19:30', endTime: '22:30', prices: { svip: 4000000, vip: 3000000, a: 2000000, b: 1200000 } },
  { title: 'Birthday Show: Bạch Khanh', layout: 'zones', map: 'hall-grid', time: '20:00', endTime: '22:30', prices: { svip: 2500000, vip: 1800000, a: 1200000, b: 850000 } },
  { title: 'Dạ Quang — Live Show', layout: 'zones', map: 'hall-grid', prices: { svip: 3000000, vip: 2200000, a: 1500000, b: 990000 } },

  /* ---------------- Chọn ghế ---------------- */
  {
    title: 'Khi Di sản hoá Vũ điệu',
    category: 'san-khau',
    layout: 'seats',
    map: 'nha-hat-lon',
    prices: { diamond: 3600000, gold: 2800000, silver: 2100000, bronze: 1600000 },
    shows: [
      { date: '2026-11-07', time: '19:30', endTime: '21:30' },
      { date: '2026-11-14', time: '19:30', endTime: '21:30' },
    ],
  },
  { title: 'Ánh Kim — Reunion', layout: 'seats', map: 'nha-hat-lon', prices: { diamond: 3200000, gold: 2500000, silver: 1800000, bronze: 1200000 } },
  { title: 'Nhạc kịch “Phố Đèn Lồng”', category: 'san-khau', layout: 'seats', map: 'nha-hat-lon', prices: { diamond: 2400000, gold: 1800000, silver: 1200000, bronze: 750000 } },
  {
    title: 'Vở diễn: Xóm Trọ Lắm Trò',
    category: 'san-khau',
    layout: 'seats',
    map: 'san-khau-nho',
    prices: { vip: 350000, thuong: 250000 },
    shows: [
      { date: '2026-11-08', time: '14:30', endTime: '17:00' },
      { date: '2026-11-08', time: '19:30', endTime: '22:00' },
      { date: '2026-11-15', time: '19:30', endTime: '22:00' },
    ],
  },
  { title: 'Kịch: Tấm Cám Đại Chiến', category: 'san-khau', layout: 'seats', map: 'san-khau-nho', prices: { vip: 320000, thuong: 220000 } },

  /* ---------------- Chỉ chọn loại vé (không sơ đồ) ---------------- */
  {
    title: 'Kịch: Hẹn Anh Ở Bến Sông',
    category: 'san-khau',
    venue: 'Sân khấu kịch [ĐỊA ĐIỂM]',
    description: [
      'Vở kịch tâm lý xã hội xoay quanh một bến sông miền Tây, nơi những con người tưởng chừng xa lạ có chung một lời hẹn chưa thành.',
      'Tác giả & đạo diễn: [TÊN]. Với sự tham gia của các nghệ sĩ: [DANH SÁCH NGHỆ SĨ].',
    ],
    shows: [
      { date: '2026-11-15', time: '16:00', endTime: '19:00' },
      { date: '2026-11-21', time: '20:00', endTime: '23:00' },
    ],
    tiers: [
      { id: 'vip', name: 'VIP', price: 360000, perks: 'Ghế ngồi tầng trệt, 5 hàng đầu.', remaining: 40, max: 6 },
      { id: 'thuong', name: 'Vé thường', price: 330000, perks: 'Ghế ngồi tầng trệt.', remaining: 120, max: 6 },
      { id: 'thuong-lau', name: 'Vé thường (trên lầu)', price: 330000, perks: 'Ghế ngồi tầng lầu.', remaining: 90, max: 6 },
    ],
  },
]
