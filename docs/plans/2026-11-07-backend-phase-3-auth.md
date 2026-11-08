# Backend giai đoạn 3: Đăng nhập & Tài khoản — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết lại 6 API tài khoản của server Node (`/auth/me|register|login|logout|forgot|reset`) bằng FastAPI + PostgreSQL. Giữ nguyên đường dẫn, JSON, mã HTTP, câu báo lỗi tiếng Việt và cơ chế phiên cookie, để giao diện React (`AuthModal`, `AuthProvider`) không phải sửa gì. Cung cấp dependency phân quyền cho các giai đoạn sau.

**Architecture:**
- Kiểm tra dữ liệu dùng hàm thuần, nằm ở `app/validators.py`.
- Phiên đăng nhập và phân quyền nằm ở `app/auth.py`: token ngẫu nhiên, DB chỉ lưu sha256, cookie httpOnly `tn_session` có hạn 30 ngày.
- Giới hạn đăng nhập sai nằm ở `app/ratelimit.py`, lưu trong bộ nhớ và cho phép thay đồng hồ khi test.
- Router ở `app/routers/auth.py`.
- Middleware chỉ nhận JSON cho request ghi dữ liệu, để chống CSRF cùng với cookie SameSite=Lax.

**Tech Stack:** FastAPI, SQLAlchemy 2.1 (đồng bộ), `hashlib.scrypt` (`app/security.py` đã có), pytest + `TestClient` (giữ cookie giữa các request).

**Spec:** `docs/superpowers/specs/2026-11-06-fastapi-postgres-migration-design.md` (mục 6 "Đăng nhập", mục 7 dòng giai đoạn 3). Nguồn hành vi chuẩn: `server/auth.js` (dòng 30–143), `server/app.js` (dòng 144–236).

## Global Constraints

- Không sửa `server/`, `src/`. **Không tạo git commit** (theo yêu cầu người dùng). Tiến độ ghi vào ledger.
- Đường dẫn NFD: `cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip`. Tạo file bằng Write vào scratchpad rồi `cp`, vì heredoc Bash dễ hỏng với tiếng Việt và dấu `\`.
- Test: `cd backend && .venv/Scripts/python.exe -m pytest -p no:cacheprovider`.
- Lỗi luôn trả `{"error": "..."}`, dùng đúng các câu dưới đây (chép nguyên văn từ Node):
  - 400 `Vui lòng nhập họ và tên (2–80 ký tự)`
  - 400 `Email hoặc số điện thoại không hợp lệ`
  - 400 `Mật khẩu tối thiểu 6 ký tự`
  - 400 `Mật khẩu tối đa 128 ký tự`
  - 409 `Email này đã được đăng ký`
  - 409 `Số điện thoại này đã được đăng ký`
  - 400 `Vui lòng nhập email/số điện thoại và mật khẩu`
  - 401 `Email/số điện thoại hoặc mật khẩu không đúng`
  - 429 `Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau {N} phút.`
  - 400 `Liên kết đặt lại mật khẩu đã hết hạn hoặc không hợp lệ`
  - 401 `Vui lòng đăng nhập để tiếp tục`
  - 403 `Tài khoản của bạn không có quyền truy cập khu vực này`
  - 415 `Yêu cầu phải gửi dạng JSON`
- Cookie: tên `tn_session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age=2592000` (30 ngày). Có `Secure` khi `ENV=prod`.
- Token phiên và token đặt lại: `secrets.token_urlsafe(32)`. DB chỉ lưu `sha256(token).hexdigest()`. Hạn token đặt lại: 15 phút.
- Khoá đăng nhập: sai 5 lần thì khoá 15 phút, tính riêng cho mỗi cặp `ip|email-hoặc-sđt`.
- Dạng người dùng trả về: `{"id","name","email","phone","role"}`.
- Thân request nhận kiểu `Any` rồi ép về chuỗi giống `str()` của Node: không phải chuỗi thì coi là `""`. Nhờ vậy câu báo lỗi giống Node, không rơi về câu 400 chung.

## Review Focus

1. **Phiên đã hết hạn** (`expires_at` ở quá khứ) phải được coi như chưa đăng nhập: `/auth/me` trả `{"user": null}`, route cần đăng nhập trả 401. Test thuộc Task 2.
2. **Email khác hoa thường hoặc có khoảng trắng**: đăng ký bằng `" An@X.VN "` thì lưu là `an@x.vn`, và đăng nhập bằng `an@x.vn` vẫn được. Test thuộc Task 3 và 4.
3. **Số điện thoại viết nhiều kiểu** (`+84 912.345.678`, `0912 345 678`) phải là cùng một tài khoản với `0912345678`: đăng ký trùng thì 409, đăng nhập thì được. Test thuộc Task 3 và 4.
4. **Token đặt lại dùng lần thứ hai hoặc đã hết hạn** thì trả 400. Sau khi đặt lại, mọi phiên cũ hết hiệu lực. Test thuộc Task 5.
5. **Không làm lộ tài khoản nào tồn tại**: đăng nhập tài khoản không tồn tại nhận đúng câu lỗi như sai mật khẩu, và vẫn chạy scrypt với hash giả. `/auth/forgot` trả cùng một dạng dù tài khoản có hay không (ở môi trường dev chỉ thêm `devResetUrl` khi tồn tại, giống Node). Test thuộc Task 4 và 5.

---

### Task 1: Hàm kiểm tra dữ liệu (`app/validators.py`)

**Files:** Create `backend/app/validators.py`, `backend/tests/test_validators.py`

**Interfaces — Produces:**
- `as_str(v: Any) -> str`: trả `v` nếu là `str`, ngược lại trả `""`.
- `normalize_phone(v: Any) -> str`: bỏ `[\s.-]`, đổi `^\+84` thành `0`.
- `parse_identifier(v: Any) -> dict | None`:
  - Có `@` thì `{"email": lower(strip)}`, nhưng chỉ khi khớp `^[^\s@]+@[^\s@]+\.[^\s@]{2,}$` và dài ≤ 254.
  - Không có `@` thì `{"phone": "0xxxxxxxxx"}` nếu khớp `^0(3|5|7|8|9)\d{8}$`.
  - Còn lại trả `None`.
- `is_email(v) -> bool`, `is_phone(v) -> bool`.
- `check_password(pw: str) -> None`: ném `HTTPException(400, ...)` với 2 câu về độ dài.

- [ ] **Step 1: Test thất bại**

```python
@pytest.mark.parametrize("raw,expected", [
    (" An@X.VN ", {"email": "an@x.vn"}), ("+84 912.345.678", {"phone": "0912345678"}),
    ("0912-345-678", {"phone": "0912345678"}), ("0212345678", None), ("a@b.c", None), ("", None), (123, None),
    ("x" * 250 + "@a.vn", None)])
def test_parse_identifier(raw, expected): assert parse_identifier(raw) == expected

@pytest.mark.parametrize("pw,msg", [("12345", "Mật khẩu tối thiểu 6 ký tự"), ("x" * 129, "Mật khẩu tối đa 128 ký tự")])
def test_check_password_messages(pw, msg):
    with pytest.raises(HTTPException) as e: check_password(pw)
    assert e.value.status_code == 400 and e.value.detail == msg

def test_check_password_accepts_6_to_128(): check_password("123456"); check_password("x" * 128)
def test_as_str(): assert as_str(5) == "" and as_str(None) == "" and as_str("a") == "a"
```
- [ ] **Step 2: FAIL** (ImportError) → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** → ghi ledger.

---

### Task 2: Phiên, dependency phân quyền, middleware chỉ nhận JSON (`app/auth.py`)

**Files:**
- Create: `backend/app/auth.py`, `backend/tests/test_auth_session.py`
- Modify: `backend/app/main.py` (thêm middleware JSON-only), `backend/app/config.py` (nếu cần hằng số)

**Interfaces — Produces:**
- `COOKIE = "tn_session"`, `SESSION_TTL = timedelta(days=30)`.
- `sha256_hex(s: str) -> str`, `new_token() -> str`.
- `public_user(u: User) -> dict`.
- `create_session(db: Session, response: Response, user_id: int) -> None`: chèn `UserSession`, đặt cookie theo Global Constraints.
- `destroy_session(db, request: Request, response: Response) -> None`: xoá dòng phiên và xoá cookie (cùng `path` / `samesite`).
- Dependency:
  - `current_user(request, db) -> User | None`: phiên hợp lệ và `expires_at > now()`.
  - `require_user(user = Depends(current_user)) -> User`: 401 nếu chưa đăng nhập.
  - `require_role(*roles: str) -> Callable`: trả về dependency, 401 nếu chưa đăng nhập, 403 nếu sai vai trò.
- Middleware `json_only` trong `main.py`: với `/api/*` có phương thức khác `GET`/`HEAD`/`OPTIONS` mà `content-type` không bắt đầu bằng `application/json` thì trả 415 `{"error": "Yêu cầu phải gửi dạng JSON"}`.

- [ ] **Step 1: Test thất bại**. Dùng router chỉ dành cho test (gắn trong fixture, gỡ ra sau test, giống `test_errors.py`):
  - `GET /api/_probe/me` (`require_user`)
  - `GET /api/_probe/admin` (`require_role("admin")`)
  - `POST /api/_probe/echo`
  - Fixture `user_factory(db, role="customer") -> User` ghi vào DB test bằng `api_db`/commit, dọn sau test.

```python
def test_require_user_401_without_cookie(probe): r = probe.get("/api/_probe/me"); assert r.status_code == 401 and r.json() == {"error": "Vui lòng đăng nhập để tiếp tục"}
def test_valid_session_passes(probe, logged_in_customer): assert probe.get("/api/_probe/me").json()["role"] == "customer"
def test_expired_session_is_logged_out(probe, session_expired): assert probe.get("/api/_probe/me").status_code == 401
def test_role_forbidden_403(probe, logged_in_customer): assert probe.get("/api/_probe/admin").json() == {"error": "Tài khoản của bạn không có quyền truy cập khu vực này"}
def test_admin_allowed(probe, logged_in_admin): assert probe.get("/api/_probe/admin").status_code == 200
def test_token_stored_hashed(db_rows_after_login): assert raw_cookie_token not in stored hashes and sha256_hex(raw) in stored
def test_cookie_attributes(set_cookie_header): assert "HttpOnly" in h and "SameSite=lax" in h.lower()... and "Max-Age=2592000" in h and "Path=/" in h
def test_non_json_write_is_415(probe): r = probe.post("/api/_probe/echo", data="a=1", headers={"content-type": "application/x-www-form-urlencoded"}); assert r.status_code == 415
def test_json_write_passes(probe): assert probe.post("/api/_probe/echo", json={}).status_code == 200
```
  Để đăng nhập trong test, fixture `logged_in_*` gọi trực tiếp `create_session` với một `Response` giả, rồi gắn cookie vào client (`client.cookies.set(COOKIE, token)`). Chưa phụ thuộc vào route login.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ** (test của giai đoạn 0–2 vẫn pass, các GET danh mục không bị middleware chặn) → ghi ledger.

---

### Task 3: `GET /auth/me`, `POST /auth/register`, `POST /auth/logout`

**Files:** Create `backend/app/routers/auth.py`, `backend/tests/test_api_auth_register.py`. Modify `backend/app/main.py` (`include_router(auth.router, prefix="/api")`), Postman.

**Interfaces — Produces:** `app.routers.auth.router` (tag "Tài khoản"). Body: `RegisterIn{name: Any = "", identifier: Any = "", password: Any = ""}`.
- `GET /auth/me` → `{"user": public_user | null}`. Luôn 200.
- `POST /auth/register`:
  - Kiểm tra theo thứ tự: tên 2–80 ký tự (sau `strip`), identifier, mật khẩu, trùng tài khoản (409 với câu email hoặc sđt).
  - Hợp lệ thì chèn `User` với `hash_password`, tạo phiên, trả 201 `{"user": …}`.
  - Nếu hai request chạy song song cùng vượt qua bước kiểm tra trùng thì bắt `IntegrityError` và trả đúng câu 409.
- `POST /auth/logout` → `{"ok": true}`. Xoá phiên và cookie. Chưa đăng nhập cũng trả 200.

- [ ] **Step 1: Test thất bại** (client mới cho mỗi test, giữ cookie)

```python
def test_register_email_creates_user_and_logs_in(c):
    r = c.post("/api/auth/register", json={"name": " Nguyễn An ", "identifier": " An@X.VN ", "password": "matkhau1"})
    assert r.status_code == 201 and r.json()["user"] | {"id": 0} == {"id": 0, "name": "Nguyễn An", "email": "an@x.vn", "phone": None, "role": "customer"}
    assert c.get("/api/auth/me").json()["user"]["email"] == "an@x.vn"
def test_register_duplicate_email_case_insensitive_409(c)        # "AN@x.vn" → "Email này đã được đăng ký"
def test_register_duplicate_phone_any_format_409(c)              # "0912345678" rồi "+84 912 345 678" → "Số điện thoại này đã được đăng ký"
@pytest.mark.parametrize("body,msg", [({"name": "A", ...}, "Vui lòng nhập họ và tên (2–80 ký tự)"), ({"identifier": "abc"}, "Email hoặc số điện thoại không hợp lệ"),
                                      ({"password": "123"}, "Mật khẩu tối thiểu 6 ký tự"), ({"name": 123}, "Vui lòng nhập họ và tên (2–80 ký tự)")])
def test_register_validation_messages(c, body, msg)
def test_password_stored_as_scrypt(c, api_db)                    # users.password_hash bắt đầu "scrypt$", verify_password đúng
def test_me_anonymous_is_null(c): assert c.get("/api/auth/me").json() == {"user": None}
def test_logout_clears_cookie_and_session(c, api_db)             # sau logout: /me → null; bảng sessions không còn token đó
def test_malformed_json_400(c): r = c.post("/api/auth/register", content="{", headers={"content-type": "application/json"}); assert r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}
```
  Fixture `c`: `TestClient(app)` mới dùng engine test. Teardown xoá mọi user không phải admin do test tạo, ví dụ `DELETE FROM users WHERE email LIKE '%@x.vn' OR phone LIKE '09123456%'`.
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.**
- [ ] **Step 5:** Thêm Postman thư mục "2 · Tài khoản": Đăng ký (POST, body JSON) và "Tôi là ai" (`/auth/me`). Postman tự giữ cookie. Cập nhật script `postman_add.py` để nhận thêm method và body. Ghi ledger.

---

### Task 4: `POST /auth/login` + chống dò mật khẩu (`app/ratelimit.py`)

**Files:** Create `backend/app/ratelimit.py`, `backend/tests/test_api_auth_login.py`. Modify `routers/auth.py`, Postman.

**Interfaces — Produces:**
- `class LoginLimiter(max_fails=5, lock=timedelta(minutes=15), clock=time.monotonic)` có:
  - `check(key) -> None`: ném 429 với số phút làm tròn lên (`ceil`).
  - `fail(key) -> None`.
  - `clear(key) -> None`.
- `app.ratelimit.login_limiter` là biến dùng chung toàn app. Test có thể thay bằng một limiter dùng đồng hồ giả qua `app.dependency_overrides[get_login_limiter]`.
- `DUMMY_HASH`: tạo một lần lúc import module, bằng `hash_password(token ngẫu nhiên)`.
- Thứ tự xử lý `POST /auth/login`:
  1. Kiểm tra identifier và password có hay không (400).
  2. `limiter.check(f"{client_ip}|{email or phone}")`.
  3. `verify_password(pw, user.hash if user else DUMMY_HASH)`.
  4. Sai thì `fail` rồi trả 401. Đúng thì `clear`, tạo phiên, trả `{"user": …}`.
- `client_ip`: lấy `request.client.host`.

- [ ] **Step 1: Test thất bại**

```python
def test_login_with_email_any_case(c, registered)                 # đăng ký an@x.vn, login "AN@X.VN" → 200, /me có user
def test_login_with_phone_any_format(c, registered_phone)          # login "+84 912 345 678"
def test_wrong_password_and_unknown_user_same_401(c, registered):
    msg = {"error": "Email/số điện thoại hoặc mật khẩu không đúng"}
    assert c.post(LOGIN, json={"identifier": "an@x.vn", "password": "saiiii"}).json() == msg
    assert c.post(LOGIN, json={"identifier": "khongco@x.vn", "password": "saiiii"}).json() == msg
def test_missing_fields_400(c)                                    # → "Vui lòng nhập email/số điện thoại và mật khẩu"
def test_fifth_failure_locks_for_15_minutes(c, fake_clock_limiter, registered):
    for _ in range(5): c.post(LOGIN, json=WRONG)
    r = c.post(LOGIN, json=RIGHT)   # cả mật khẩu đúng cũng bị chặn khi đang khoá
    assert r.status_code == 429 and r.json() == {"error": "Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút."}
    fake_clock_limiter.advance(minutes=15, seconds=1); assert c.post(LOGIN, json=RIGHT).status_code == 200
def test_success_resets_fail_counter(c, fake_clock_limiter, registered)   # 4 sai → 1 đúng → 4 sai nữa vẫn chưa khoá
def test_lock_is_per_identifier(c, fake_clock_limiter, registered)        # khoá an@x.vn không ảnh hưởng tài khoản khác
def test_unknown_user_still_runs_scrypt(monkeypatch, c)                   # đếm số lần gọi verify_password = 1
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.**
- [ ] **Step 5:** Thêm Postman "Đăng nhập" và "Đăng xuất". Ghi ledger.

---

### Task 5: `POST /auth/forgot`, `POST /auth/reset`

**Files:** Create `backend/tests/test_api_auth_reset.py`. Modify `routers/auth.py`, Postman, `backend/README.md` (mục "API tài khoản").

**Interfaces — Produces:**
- `POST /auth/forgot {identifier}`:
  - Identifier sai định dạng thì 400.
  - Tài khoản tồn tại: chèn `PasswordReset(token_hash, user_id, expires_at = now + 15 phút)` và ghi log liên kết `"{base_url}/?reset={token}"` (dùng `logging`, không `print`).
  - Luôn trả `{"ok": true}`. Riêng khi `ENV=dev` **và** tài khoản tồn tại thì thêm `"devResetUrl"`.
  - `base_url` lấy từ `request.base_url` (bỏ `/` ở cuối).
- `POST /auth/reset {token, password}`:
  - Tìm theo `sha256(token)`. Không có, đã dùng, hoặc hết hạn thì 400 với câu cố định.
  - Kiểm tra mật khẩu bằng `check_password`.
  - Trong **một transaction**: cập nhật `password_hash`, đặt `used = true`, xoá mọi `sessions` của user.
  - Sau đó tạo phiên mới và trả `{"user": …}`.

- [ ] **Step 1: Test thất bại**

```python
def test_forgot_same_shape_for_unknown_account(c):   # {"ok": True} không có devResetUrl
def test_forgot_dev_returns_reset_url(c, registered): url = r.json()["devResetUrl"]; assert "/?reset=" in url
def test_forgot_bad_identifier_400(c)
def test_reset_changes_password_and_logs_in(c, registered)       # token từ devResetUrl → reset → /me có user; login mật khẩu mới OK, cũ 401
def test_reset_invalidates_other_sessions(c, other_client, registered)   # other_client đang đăng nhập → sau reset /me của nó = null
def test_reset_token_single_use(c, registered)                   # dùng lần 2 → 400 "Liên kết đặt lại mật khẩu đã hết hạn hoặc không hợp lệ"
def test_reset_token_expired(c, registered, api_db)              # chỉnh expires_at về quá khứ → 400
def test_reset_short_password_400_and_token_still_usable(c, registered)  # mật khẩu "123" → 400 (câu độ dài); token chưa bị đánh dấu used
def test_reset_token_stored_hashed(c, registered, api_db)
```
- [ ] **Step 2: FAIL** → **Step 3: cài đặt** → **Step 4: PASS toàn bộ.**
- [ ] **Step 5:** Thêm Postman "Quên mật khẩu" và "Đặt lại mật khẩu". Request đặt lại có biến `{{resetToken}}`, được lấy từ `devResetUrl` bằng test script của request trước. README thêm bảng 6 endpoint. Chạy thử bằng `uvicorn`: gọi lần lượt register → me → logout → login → forgot → reset bằng curl kèm cookie jar. Ghi ledger.

---

## Kết thúc giai đoạn 3
- `pytest` pass toàn bộ. Test của giai đoạn 0–2 không đổi.
- Postman "2 · Tài khoản" chạy tuần tự được (cookie tự giữ).
- Giao diện React chưa đổi, đến giai đoạn 6 mới chuyển proxy. Mã lỗi và câu báo lỗi giống hệt Node, nên `AuthModal` dùng thẳng được.
