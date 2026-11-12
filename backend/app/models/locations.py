"""Đơn vị hành chính sau sáp nhập 01/07/2025 (2 cấp: tỉnh / thành phố → phường / xã / đặc khu).

Dữ liệu tham chiếu, nạp một lần ở migration 0010 từ backend/seed/locations_2025.json — KHÔNG bị seed.reset_all xoá.
"""
from sqlalchemy import ForeignKey, Index, Integer, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Province(Base):
    __tablename__ = "provinces"

    code: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)  # "Thành phố Hà Nội"
    short_name: Mapped[str] = mapped_column(Text, unique=True)  # "Hà Nội", "TP.HCM" — chính là events.city
    division_type: Mapped[str] = mapped_column(Text)


class Ward(Base):
    __tablename__ = "wards"
    __table_args__ = (
        # đích của khoá ngoại ghép events(province_code, ward_code): phường phải thuộc đúng tỉnh
        UniqueConstraint("province_code", "code", name="uq_wards_province_code"),
        Index("ix_wards_province_name", "province_code", "name"),
    )

    code: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    province_code: Mapped[int] = mapped_column(SmallInteger, ForeignKey("provinces.code"))
    name: Mapped[str] = mapped_column(Text)  # "Phường Ba Đình"
    division_type: Mapped[str] = mapped_column(Text)


REFERENCE_TABLES = ("provinces", "wards")
