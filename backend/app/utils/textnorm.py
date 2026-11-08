"""Bỏ dấu tiếng Việt để tìm kiếm — giống hệt normalizeVi trong src/lib/utils.js"""
import re
import unicodedata

_COMBINING = re.compile(f"[{chr(0x300)}-{chr(0x36F)}]")  # các dấu kết hợp U+0300..U+036F


def normalize_vi(s: str) -> str:
    """"Hà Nội" → "ha noi" (NFD, bỏ dấu kết hợp, đ→d, chữ thường, cắt khoảng trắng hai đầu)"""
    s = _COMBINING.sub("", unicodedata.normalize("NFD", s or ""))
    return s.replace("đ", "d").replace("Đ", "D").lower().strip()


def slugify(s: str) -> str:
    """Giống slugify trong src/lib/events.js: "Đêm Nhạc 2026" → "dem-nhac-2026" """
    return re.sub(r"[^a-z0-9]+", "-", normalize_vi(s)).strip("-")


def search_text_for(title: str, city: str, venue: str, category_label: str) -> str:
    """Cột events.search_text — cùng công thức với backend/seed/export_catalog.mjs"""
    return normalize_vi(f"{title} {city} {venue} {category_label}")
