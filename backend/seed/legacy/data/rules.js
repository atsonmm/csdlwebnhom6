/* Quy tắc bán vé — dùng chung cho giao diện (src/) và máy chủ (server/) */

/** Số vé tối đa mỗi đơn hàng */
export const MAX_PER_ORDER = 10

/** Thời gian giữ vé ở bước thanh toán (phút) */
export const HOLD_MINUTES = 15

/** Mã giảm giá: amount = số tiền giảm, minOrder = giá trị đơn tối thiểu (VND) */
export const COUPONS = {
  NHIP50: { amount: 50000, minOrder: 500000 },
}

export const PAYMENT_METHODS = ['qr', 'wallet', 'card']
