/** Ghép className, bỏ qua giá trị falsy */
export const cn = (...classes) => classes.filter(Boolean).join(' ')

/** Bỏ dấu tiếng Việt để tìm kiếm không phân biệt dấu: "Hà Nội" -> "ha noi" */
export const normalizeVi = (str = '') =>
  str
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim()
