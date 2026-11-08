# Hướng dẫn làm việc chung trên repo

Tài liệu này quy định cách cả nhóm làm việc với Git và GitHub trong dự án `csdlwebnhom6`.
**Mọi thành viên đọc kỹ trước khi bắt đầu code.**

---

## Mục lục

1. [Giải thích các từ hay dùng](#1-giải-thích-các-từ-hay-dùng)
2. [Nguyên tắc vàng](#2-nguyên-tắc-vàng)
3. [Chuẩn bị lần đầu](#3-chuẩn-bị-lần-đầu)
4. [Quy trình mỗi lần làm một việc](#4-quy-trình-mỗi-lần-làm-một-việc)
5. [Cách đặt tên nhánh](#5-cách-đặt-tên-nhánh)
6. [Cách viết lời commit](#6-cách-viết-lời-commit)
7. [Tạo và xem lại Pull Request](#7-tạo-và-xem-lại-pull-request)
8. [Xử lý các tình huống thường gặp](#8-xử-lý-các-tình-huống-thường-gặp)
9. [Quy định về file `.env`](#9-quy-định-về-file-env)
10. [Những điều KHÔNG được làm](#10-những-điều-không-được-làm)
11. [Bảng lệnh tóm tắt](#11-bảng-lệnh-tóm-tắt)

---

## 1. Giải thích các từ hay dùng

<!-- prettier-ignore -->
| Từ | Ý nghĩa | 
|---|---|
| **Git** | Phần mềm cài trên máy, dùng để lưu lại lịch sử thay đổi của code. |
| **GitHub** | Trang web lưu code trên mạng để cả nhóm dùng chung. |
| **Repo** | "Kho chứa" của dự án. Có một bản trên GitHub (gọi là **origin**) và một bản trên máy mỗi người. |
| **Commit** | Một lần lưu lại các thay đổi, kèm một câu mô tả. |
| **Branch** (nhánh) | Một bản sao song song của code để làm riêng mà không ảnh hưởng người khác. |
| **main** | Nhánh chính, là bản chính thức của dự án. Code trên `main` **luôn phải chạy được**. |
| **Clone** | Tải repo từ GitHub về máy lần đầu tiên. |
| **Pull** | Kéo thay đổi mới nhất từ GitHub về máy. |
| **Push** | Đẩy các commit trên máy lên GitHub. |
| **Pull Request (PR)** | Yêu cầu gộp code từ nhánh của mình vào `main`, để người khác xem lại trước khi gộp. |
| **Review** | Việc người khác xem lại code trong PR và góp ý. |
| **Approve** | Người xem lại bấm "đồng ý" cho PR. |
| **Merge** | Gộp code từ nhánh này vào nhánh khác. |
| **Squash** | Cách gộp "nén" tất cả commit trong một PR thành **1 commit duy nhất** trên `main`. Nhóm mình chỉ dùng cách này. |
| **Conflict** (xung đột) | Xảy ra khi hai người cùng sửa một chỗ trong cùng một file, cần tự chọn giữ bản nào. |

---

## 2. Nguyên tắc vàng

> 1. **Không ai sửa hoặc push thẳng lên `main`.**
> 2. **Mỗi việc làm trên một nhánh riêng.**
> 3. **Muốn gộp vào `main` thì phải tạo Pull Request và được ít nhất 1 người khác Approve.**
> 4. **Không tự Merge PR của chính mình** khi chưa có ai Approve.

> ℹ️ Repo đang để riêng tư (private) với gói miễn phí nên GitHub **không tự chặn** những việc trên.
> Cả nhóm cần **tự giác** tuân thủ.

---

## 3. Chuẩn bị lần đầu

### 3.1. Cài Git

Tải tại <https://git-scm.com> rồi cài theo mặc định.

### 3.2. Khai báo tên và email

Email nên trùng với email tài khoản GitHub.

```bash
git config --global user.name "Ten Cua Ban"
git config --global user.email "email@cuaban.com"
```

### 3.3. Tải repo về máy

```bash
git clone <đường-link-repo>
cd csdlwebnhom6
```

Đường link lấy ở nút xanh **Code** trên trang repo.
Lần đầu push, GitHub sẽ mở trình duyệt để bạn đăng nhập.

### 3.4. Tạo file `.env`

Copy file mẫu rồi điền thông tin của máy mình:

- `backend/.env.example` → `backend/.env`
- `frontend/.env.example` → `frontend/.env`

Xem thêm [Mục 9](#9-quy-định-về-file-env).

---

## 4. Quy trình mỗi lần làm một việc

Ví dụ: bạn được giao **làm trang đăng nhập**.

### Bước 1: Về `main` và cập nhật code mới nhất

```bash
git switch main
git pull origin main
```

### Bước 2: Tạo nhánh mới cho việc này

```bash
git switch -c feature/trang-dang-nhap
```

### Bước 3: Viết code và chạy thử trên máy

### Bước 4: Lưu lại (commit)

```bash
git status                 # xem những file đã thay đổi, LUÔN kiểm tra trước khi add
git add .                  # chọn tất cả thay đổi để chuẩn bị lưu
git commit -m "feat: them giao dien trang dang nhap"
```

Nên commit **nhiều lần nhỏ**, mỗi lần một ý.

### Bước 5: Đẩy nhánh lên GitHub

```bash
git push -u origin feature/trang-dang-nhap   # lần đầu đẩy nhánh này
git push                                     # những lần sau
```

### Bước 6: Tạo Pull Request

Lên trang repo → bấm **Compare & pull request** → điền theo [Mục 7](#7-tạo-và-xem-lại-pull-request).

### Bước 7: Chờ review và sửa theo góp ý

Sửa trên máy → `add` → `commit` → `push`. PR sẽ **tự cập nhật**, không cần tạo PR mới.

### Bước 8: Gộp và dọn dẹp

Khi đã được Approve và mọi góp ý đã được xử lý:

1. Bấm **Squash and merge** → **Confirm**.
2. Nhánh trên GitHub sẽ tự xóa (nếu không, bấm **Delete branch**).
3. Trên máy:

```bash
git switch main
git pull origin main
git branch -d feature/trang-dang-nhap
```

➡️ Việc tiếp theo thì quay lại **Bước 1**, và **luôn tạo nhánh mới**, không dùng lại nhánh cũ.

---

## 5. Cách đặt tên nhánh

Viết **thường, không dấu**, các từ nối bằng **gạch ngang `-`**.

| Tiền tố     | Dùng khi                                   | Ví dụ                            |
| ----------- | ------------------------------------------ | -------------------------------- |
| `feature/`  | Làm tính năng mới                          | `feature/trang-gio-hang`         |
| `fix/`      | Sửa lỗi                                    | `fix/loi-dang-nhap-sai-mat-khau` |
| `style/`    | Chỉnh giao diện, không đổi chức năng       | `style/chinh-mau-header`         |
| `refactor/` | Viết lại code cho gọn, không đổi chức năng | `refactor/tach-component-navbar` |
| `docs/`     | Sửa tài liệu                               | `docs/cap-nhat-readme`           |
| `chore/`    | Việc lặt vặt: cài thư viện, cấu hình       | `chore/cai-axios`                |

---

## 6. Cách viết lời commit

Cấu trúc: `loại: mô tả ngắn gọn việc đã làm`

| Loại       | Ý nghĩa                                  |
| ---------- | ---------------------------------------- |
| `feat`     | Thêm tính năng mới                       |
| `fix`      | Sửa lỗi                                  |
| `style`    | Chỉnh giao diện hoặc định dạng code      |
| `refactor` | Viết lại code, không đổi chức năng       |
| `docs`     | Sửa tài liệu                             |
| `chore`    | Việc lặt vặt (cài thư viện, cấu hình...) |

✅ Tốt:

```
feat: them form dang ky tai khoan
fix: sua loi nut dang nhap khong bam duoc
style: canh giua logo tren header
```

❌ Không tốt:

```
sua
update
abc
```

---

## 7. Tạo và xem lại Pull Request

### 7.1. Người tạo PR

- **base:** `main` ← **compare:** nhánh của bạn.
- **Tiêu đề:** ngắn gọn, ví dụ `Làm trang đăng nhập`.
- **Mô tả:** điền theo mẫu sau:

```markdown
## Đã làm gì

- ...

## Cách chạy thử

- ...

## Ảnh chụp màn hình (nếu có giao diện)

## Ghi chú

- (biến mới trong .env, thư viện mới cần cài, ...)
```

- Bên phải chọn **Reviewers**: ít nhất 1 người trong nhóm.
- Nhắn cho người đó biết để PR không bị bỏ quên.

**Tự kiểm tra trước khi tạo PR:**

- [ ] Đã chạy thử, không có lỗi.
- [ ] Đã cập nhật code mới nhất từ `main` (`git pull origin main`).
- [ ] Không có file `.env`, `node_modules/` hoặc file rác trong thay đổi.
- [ ] Đã xóa các dòng `console.log` dùng để thử.
- [ ] PR chỉ làm **một việc**.
- [ ] Nếu thêm biến môi trường mới, đã thêm tên biến vào `.env.example`.

### 7.2. Người xem lại (reviewer)

- Vào tab **Files changed** để xem từng dòng đã sửa.
- Góp ý lịch sự, cụ thể, nói rõ chỗ nào và nên sửa thế nào.
- Nếu ổn thì bấm **Review changes → Approve**.
- Nếu cần sửa thì bấm **Request changes** và ghi rõ lý do.

### 7.3. Trước khi gộp

- Có ít nhất **1 Approve** từ người khác.
- Mọi góp ý đã được bấm **Resolve conversation**.
- Chỉ dùng **Squash and merge**.

---

## 8. Xử lý các tình huống thường gặp

### 8.1. `main` đã có code mới trong lúc mình đang làm

Đứng ở nhánh của mình rồi chạy:

```bash
git pull origin main
```

Nên làm việc này **mỗi ngày một lần** để tránh xung đột lớn.

### 8.2. Bị xung đột (conflict)

Trong file sẽ xuất hiện:

```
<<<<<<< HEAD
code của bạn
=======
code của người khác
>>>>>>> main
```

1. Mở file bằng VS Code, chọn **Accept Current**, **Accept Incoming** hoặc **Accept Both**, hoặc tự sửa tay.
2. Xóa hết các dòng `<<<<<<<`, `=======`, `>>>>>>>`.
3. Chạy thử lại, rồi:

```bash
git add .
git commit -m "fix: giai quyet xung dot voi main"
git push
```

> ⚠️ Không chắc nên giữ bản nào thì **hỏi người viết đoạn code kia**. Không xóa bừa code của người khác.

### 8.3. Lỡ sửa code khi đang đứng ở `main` (chưa commit)

Tạo nhánh mới ngay, các thay đổi sẽ đi theo sang nhánh mới:

```bash
git switch -c feature/ten-viec
```

### 8.4. Không biết mình đang ở nhánh nào

```bash
git branch
```

Nhánh có dấu `*` là nhánh hiện tại. VS Code cũng hiện tên nhánh ở góc dưới bên trái.

### 8.5. Gặp lỗi lạ, không biết xử lý

**Dừng lại và hỏi nhóm.** Đừng thử các lệnh trên mạng mà mình chưa hiểu.

---

## 9. Quy định về file `.env`

- File `.env` chứa **thông tin bí mật** (mật khẩu database, khóa bí mật...). **Tuyệt đối không đưa lên GitHub.**
- File `.env.example` là **file mẫu**, chỉ có tên biến, không có giá trị thật. File này **có** đưa lên GitHub.
- Khi thêm biến mới vào `.env`, **phải thêm tên biến đó vào `.env.example`** và ghi chú trong PR.
- File `.gitignore` (danh sách file Git sẽ bỏ qua) phải luôn có các dòng:

```
.env
node_modules/
```

> 🚨 Nếu lỡ đưa `.env` lên GitHub: báo ngay cho nhóm và **đổi mật khẩu đó**.
> Xóa file đi là chưa đủ, vì người khác vẫn xem lại được trong lịch sử commit.

---

## 10. Những điều KHÔNG được làm

- ❌ Push thẳng lên `main`.
- ❌ Tự Merge PR của mình khi chưa ai Approve.
- ❌ Dùng `git push --force` hoặc `git reset --hard` khi chưa hiểu rõ. Các lệnh này có thể **làm mất code**.
- ❌ Đưa file `.env`, `node_modules/` hoặc mật khẩu lên GitHub.
- ❌ Gom nhiều việc không liên quan vào một nhánh hoặc một PR.
- ❌ Dùng lại nhánh đã gộp cho việc mới.
- ❌ Sửa phần việc của người khác mà không báo trước (đặc biệt là file dùng chung, hoặc thư mục `backend/` nếu bạn làm frontend và ngược lại).

---

## 11. Bảng lệnh tóm tắt

```
BẮT ĐẦU VIỆC MỚI:   git switch main
                    git pull origin main
                    git switch -c feature/ten-viec

TRONG LÚC LÀM:      git status
                    git add .
                    git commit -m "feat: mo ta"
                    git push              (lần đầu: git push -u origin feature/ten-viec)

CẬP NHẬT TỪ MAIN:   git pull origin main  (đứng ở nhánh của mình)

XONG VIỆC:          Tạo PR → nhờ review → Squash and merge
                    git switch main
                    git pull origin main
                    git branch -d feature/ten-viec
```

---

Có thắc mắc gì, hãy hỏi trong nhóm trước khi làm. 💪
