/* Dữ liệu mẫu — thay bằng API thật sau này */

/** Danh mục sự kiện chung — dùng cho hàng Nhạc sống / Sân khấu, lọc thành phố, kết quả tìm kiếm */
export const catalog = [
  { id: 'e1', title: 'Birthday Show: Bạch Khanh', city: 'Hà Nội', cityId: 'hn', date: '21 Th 11', price: 850, category: 'nhac-song' },
  { id: 'e2', title: 'Lễ hội Bia Thủ Công', city: 'TP.HCM', cityId: 'hcm', date: '06 Th 11', price: 1299, category: 'nhac-song' },
  { id: 'e3', title: 'Live Show: Ba Giọng Ca', city: 'Lâm Đồng', cityId: 'dl', date: '14 Th 11', price: 800, category: 'nhac-song' },
  { id: 'e4', title: 'Live Concert XV — 15 năm', city: 'TP.HCM', cityId: 'hcm', date: '14 Th 11', price: 1200, category: 'nhac-song' },
  { id: 'e5', title: 'Show thực cảnh: Cờ Lau', city: 'Hà Nội', cityId: 'hn', date: '06 Th 11', price: 175, category: 'san-khau' },
  { id: 'e6', title: 'Art workshop: Bánh Mousse', city: 'TP.HCM', cityId: 'hcm', date: '06 Th 11', price: 480, category: 'san-khau' },
  { id: 'e7', title: 'Art workshop: Tart Chanh', city: 'TP.HCM', cityId: 'hcm', date: '07 Th 11', price: 390, category: 'san-khau' },
  { id: 'e8', title: 'Kịch: Hẹn Anh Ở Bến Sông', city: 'TP.HCM', cityId: 'hcm', date: '06 Th 11', price: 330, category: 'san-khau' },
  { id: 'e9', title: 'Giải chạy Đêm Hồ Tây', city: 'Hà Nội', cityId: 'hn', date: '23 Th 11', price: 450, category: 'the-thao' },
  { id: 'e10', title: 'Futsal Cup Sài Gòn', city: 'TP.HCM', cityId: 'hcm', date: '30 Th 11', price: 120, category: 'the-thao' },
  { id: 'e11', title: 'Hội thảo Âm thanh Sân khấu', city: 'TP.HCM', cityId: 'hcm', date: '15 Th 11', price: 250, category: 'hoi-thao' },
  { id: 'e12', title: 'Workshop Làm Nến Thơm', city: 'Đà Lạt', cityId: 'dl', date: '08 Th 11', price: 290, category: 'hoi-thao' },
  { id: 'e13', title: 'Tour Đêm Phố Cổ', city: 'Hà Nội', cityId: 'hn', date: '09 Th 11', price: 199, category: 'tham-quan' },
  { id: 'e14', title: 'Săn Mây Cầu Đất', city: 'Đà Lạt', cityId: 'dl', date: '16 Th 11', price: 350, category: 'tham-quan' },
  { id: 'e15', title: 'Kịch: Ngôi Nhà Trên Đồi', city: 'Đà Lạt', cityId: 'dl', date: '28 Th 11', price: 280, category: 'san-khau' },
  { id: 'e16', title: 'Hội chợ Đồ Cũ Cuối Tuần', city: 'Huế', cityId: 'khac', date: '10 Th 11', price: 50, category: 'khac' },
  { id: 'e17', title: 'Liveshow Phố Biển', city: 'Đà Nẵng', cityId: 'khac', date: '22 Th 11', price: 700, category: 'nhac-song' },
  { id: 'e18', title: 'Đêm Đờn Ca Tài Tử', city: 'Cần Thơ', cityId: 'khac', date: '29 Th 11', price: 150, category: 'san-khau' },
]

/** Phần 7 · Lịch diễn */
export const schedules = {
  weekend: {
    heading: 'Cuối tuần này đi đâu?',
    sheet: 'LỊCH DIỄN · 07–08.11',
    items: [
      { id: 'w1', day: 'T7', time: '09:00', title: 'Triển lãm Di sản Phật giáo', venue: 'Bảo tàng [ĐỊA ĐIỂM]', price: 150 },
      { id: 'w2', day: 'T7', time: '19:30', title: 'Khi Di sản hoá Vũ điệu', venue: 'Nhà hát [ĐỊA ĐIỂM]', price: 1600 },
      { id: 'w3', day: 'CN', time: '14:30', title: 'Vở diễn: Xóm Trọ Lắm Trò', venue: 'Sân khấu [ĐỊA ĐIỂM]', price: 250 },
      { id: 'w4', day: 'CN', time: '20:00', title: 'Show thực cảnh: Cờ Lau', venue: 'Khu du lịch [ĐỊA ĐIỂM]', price: 175 },
    ],
  },
  month: {
    heading: 'Tháng này có gì hay?',
    sheet: 'LỊCH DIỄN · THÁNG 11',
    items: [
      { id: 'mo1', day: '14.11', time: '19:30', title: 'Live Concert XV — 15 năm', venue: 'Nhà thi đấu [ĐỊA ĐIỂM]', price: 1200 },
      { id: 'mo2', day: '15.11', time: '19:30', title: 'Concert Đêm 4: Tinh Hà', venue: 'Trung tâm Triển lãm [ĐỊA ĐIỂM]', price: 990 },
      { id: 'mo3', day: '21.11', time: '20:00', title: 'Birthday Show: Bạch Khanh', venue: 'Phòng trà [ĐỊA ĐIỂM]', price: 850 },
      { id: 'mo4', day: '22.11', time: '19:00', title: 'Fanmeeting “Về Nhà”', venue: 'Nhà hát [ĐỊA ĐIỂM]', price: 799 },
      { id: 'mo5', day: '29.11', time: '17:00', title: 'Lễ hội Âm nhạc Thành Phố', venue: 'Công viên [ĐỊA ĐIỂM]', price: 650 },
    ],
  },
}

/** Phần 8 · Thành phố */
export const cities = [
  { id: 'hcm', code: 'SGN', name: 'TP. Hồ Chí Minh', count: 128, tilt: '-rotate-1' },
  { id: 'hn', code: 'HAN', name: 'Hà Nội', count: 96, tilt: 'rotate-1' },
  { id: 'dl', code: 'DLI', name: 'Đà Lạt', count: 34, tilt: '-rotate-[0.5deg]' },
  { id: 'khac', code: 'VN', name: 'Nơi khác', count: 57, tilt: 'rotate-[1.5deg]' },
]

/** Phần 9 · Tờ báo Nhịp */
export const blogCategories = [
  { id: 'all', label: 'Tất cả' },
  { id: 'gi-dzay', label: 'Gì dzậy trời?' },
  { id: 'ban-tin', label: 'Bản tin tối cổ' },
  { id: 'meo', label: 'Mẹo đi show' },
  { id: 'uu-dai', label: 'Ưu đãi' },
]

export const blogPosts = [
  {
    id: 'b1',
    cat: 'ban-tin',
    kicker: 'TIN MỞ BÁN · 05.11.2026',
    title: '“Về Nhà” — đêm gặp gỡ mở bán vé từ 799.000 ₫',
    excerpt:
      'Có những đêm nhạc để nghe, và có những đêm để gặp lại nhau. Buổi fanmeeting tại [ĐỊA ĐIỂM] hứa hẹn một khoảng cách gần hơn bao giờ hết…',
  },
  {
    id: 'b2',
    cat: 'gi-dzay',
    kicker: 'TIN SẢN PHẨM',
    title: 'TicketNhịp ra mắt trang chủ mới: cả thế giới giải trí trong một xấp vé',
    excerpt: 'Giao diện mới lấy cảm hứng từ những tấm vé giấy, giúp bạn tìm sự kiện nhanh hơn và vui hơn…',
  },
  {
    id: 'b3',
    cat: 'ban-tin',
    kicker: 'BẢN TIN',
    title: 'Concert Anh Em Vượt Núi công bố đêm 3 và 4, vé từ 1 triệu đồng',
    excerpt: 'Ban tổ chức chính thức mở thêm hai đêm diễn sau khi hai đêm đầu bán hết chỉ trong 15 phút…',
  },
  {
    id: 'b4',
    cat: 'meo',
    kicker: 'MẸO ĐI SHOW',
    title: '5 điều cần biết trước khi vào hàng chờ mua vé concert',
    excerpt: 'Đăng nhập sớm, lưu sẵn phương thức thanh toán và đừng bao giờ tải lại trang khi đang trong hàng chờ…',
  },
  {
    id: 'b5',
    cat: 'uu-dai',
    kicker: 'ƯU ĐÃI',
    title: 'Quét QR thanh toán, giảm ngay 50K cho đơn từ 500K',
    excerpt: 'Nhập mã NHIP50 khi thanh toán bằng QR của ngân hàng liên kết. Số lượng có hạn mỗi ngày…',
  },
  {
    id: 'b6',
    cat: 'gi-dzay',
    kicker: 'GÌ DZẬY TRỜI?',
    title: 'Vì sao khán giả xếp hàng từ 4 giờ sáng chỉ để mua một cây lightstick?',
    excerpt: 'Chúng tôi đã dành một buổi sáng cùng những người hâm mộ kiên nhẫn nhất thành phố…',
  },
  {
    id: 'b7',
    cat: 'meo',
    kicker: 'MẸO ĐI SHOW',
    title: 'Chọn chỗ ngồi nhà hát: hàng nào nghe hay, nhìn rõ nhất?',
    excerpt: 'Không phải hàng đầu lúc nào cũng là lựa chọn tốt nhất. Đây là bí kíp từ các kỹ sư âm thanh…',
  },
  {
    id: 'b8',
    cat: 'uu-dai',
    kicker: 'ƯU ĐÃI',
    title: 'Thẻ thành viên Trạm Âm Thanh: ưu tiên mua vé trước 48 giờ',
    excerpt: 'Chủ thẻ được vào hàng chờ sớm và nhận quà tặng độc quyền tại mỗi đêm diễn…',
  },
]
