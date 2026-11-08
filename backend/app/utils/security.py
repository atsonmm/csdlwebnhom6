"""Băm mật khẩu bằng scrypt — cùng định dạng và tham số với server Node cũ
   (scrypt$<salt base64>$<key base64>, N=16384, r=8, p=1, 64 byte)"""
import base64
import hashlib
import hmac
import os

_N, _R, _P, _DKLEN = 16384, 8, 1, 64


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=64 * 1024 * 1024)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = _scrypt(password, salt)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"


def verify_password(password: str, stored: str) -> bool:
    parts = (stored or "").split("$")
    if len(parts) != 3 or parts[0] != "scrypt" or not parts[1] or not parts[2]:
        return False
    try:
        salt, expected = base64.b64decode(parts[1]), base64.b64decode(parts[2])
    except ValueError:
        return False
    return hmac.compare_digest(_scrypt(password, salt), expected)
