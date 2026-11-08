from app.utils.security import hash_password, verify_password

# Tạo bằng đúng hàm hashPassword của server/auth.js (Node, scrypt mặc định N=16384 r=8 p=1, 64 byte)
NODE_HASH = "scrypt$ZAyTUYcB+Fku9NJYmHh7ZA==$RQiGlVCm9NAYngH4D20jTfOgmyc9p7/JjqSmBhE53nDcKs8ML9Lm1OwR5gzSusp8ZHjf9QOabI79O1LiEdsKWA=="


def test_verifies_hash_made_by_node():
    assert verify_password("admin123456", NODE_HASH)
    assert not verify_password("sai-mat-khau", NODE_HASH)


def test_round_trip_and_format():
    h = hash_password("matkhau123")
    assert h.startswith("scrypt$") and h.count("$") == 2
    assert verify_password("matkhau123", h)
    assert hash_password("matkhau123") != h  # salt ngẫu nhiên


def test_malformed_hash_is_rejected():
    assert not verify_password("x", "bcrypt$abc$def")
    assert not verify_password("x", "")
