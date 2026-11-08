# Transaction & truy cập đồng thời (học phần — mục III.4)

Yêu cầu của học phần: chứng minh transaction và xử lý đồng thời **thật**, tức là **hai kết nối CSDL chạy chồng lấn nhau**. Gọi API hai lần lần lượt thì không được tính.

## Cách kiểm thử

- Helper `backend/tests/concurrency.py` → `race(engine, fn_a, fn_b, module=…, hold=0.3)`. Helper này làm như sau:
  1. Chạy hai thao tác trên **hai luồng**, mỗi luồng một `Session(engine)`, tức là một kết nối PostgreSQL riêng.
  2. Cho hai luồng xuất phát cùng lúc bằng `threading.Barrier`.
  3. Service gọi móc `_after_lock()` ngay sau khi giành được khoá dòng (`SELECT … FOR UPDATE` hoặc `UPDATE` có điều kiện). Bên đến trước **giữ khoá thêm 0,3 s**.
  4. Test đo thời gian chờ của bên thua: phải ≥ 0,25 s. Như vậy bên thua **thực sự bị chặn ở khoá** chứ không phải chạy lần lượt.
- Kiểm thử rollback: chèn lỗi vào giữa nghiệp vụ (monkeypatch một bước ghi sau), rồi đọc lại bằng **một kết nối khác** để chắc chắn không bảng nào bị ghi dở.

## Danh sách minh chứng

| Nghiệp vụ | Cơ chế | Test (2 kết nối / rollback) | Kết quả mong đợi |
|---|---|---|---|
| BTC huỷ cùng một sự kiện hai lần cùng lúc | `SELECT … FROM events … FOR UPDATE`; đổi trạng thái + hoàn tiền trong **một** transaction | `tests/test_cancel_concurrency.py::test_concurrent_cancel_two_connections` | 1 thành công, 1 bị chặn rồi 409; mỗi đơn hoàn đúng 1 lần (cùng `refunded_at`) |
| Admin gỡ và BTC huỷ cùng một sự kiện cùng lúc | như trên, dùng chung `org_events.cancel_event` | `tests/test_cancel_concurrency.py::test_admin_org_cancel_concurrent_single_refund` | 1 thắng; `cancelled_by` là bên thắng; không hoàn hai lần |
| Lỗi giữa chừng khi huỷ sự kiện | một transaction, router `commit` một lần / `rollback` khi lỗi | `tests/test_api_org_cancel.py::test_cancel_rollback_on_midway_error` | sự kiện vẫn `approved`, đơn vẫn `paid` |
| Hai yêu cầu rút tiền, mỗi cái bằng toàn bộ số dư | `SELECT … FROM organizers WHERE user_id = … FOR UPDATE` trước khi tính số dư | `tests/test_withdrawal_concurrency.py::test_concurrent_requests_two_connections` | 1 tạo được, 1 bị chặn rồi 409 "Số dư khả dụng không đủ"; `available == 0` |
| Hai yêu cầu rút tiền, mỗi cái nửa số dư | như trên (khoá không chặn sai) | `tests/test_withdrawal_concurrency.py::test_concurrent_half_requests_both_succeed` | cả hai thành công, bên sau vẫn chờ khoá |
| Lỗi giữa chừng khi tạo yêu cầu rút | một transaction | `tests/test_api_withdrawals.py::test_request_rollback_on_midway_error` | không có dòng `withdrawals` mới, số dư như cũ |
| Hai Admin duyệt cùng một yêu cầu rút (đã chuyển / từ chối) | `UPDATE withdrawals … WHERE status = 'pending' RETURNING` (khoá dòng tới khi commit) | `tests/test_api_admin_withdrawals.py::test_two_admins_decide_concurrently` | 1 thành công, 1 bị chặn rồi 409 "Yêu cầu này đã được xử lý"; `processed_by` là người thắng |
| Lỗi giữa chừng khi duyệt rút tiền | một transaction | `tests/test_api_admin_withdrawals.py::test_decide_rollback_on_midway_error` | yêu cầu vẫn `pending`, `processed_at` NULL |
| Hai Admin duyệt cùng một hồ sơ sự kiện | `UPDATE events … WHERE status = 'pending'` | `tests/test_api_admin.py::test_parallel_reviews_exactly_one_wins` | 1 thành công, 1 nhận 409 |
| Soát cùng một mã vé ở hai cổng | `UPDATE tickets SET checked_in_at = now() WHERE … AND checked_in_at IS NULL` | `tests/test_api_checkin.py::test_checkin_ok_then_already_keeps_first_time` (C1) | chỉ một lần `checked-in`, lần sau `already` kèm giờ soát đầu |
| Hai khách mua chỗ cuối / cùng ghế | `UPDATE tier_stock … WHERE presold + sold + :qty <= capacity` (sắp theo `tier_id`); `INSERT seat_holds … ON CONFLICT DO NOTHING` | `tests/test_api_orders_create.py::test_parallel_buyers_never_oversell`, `tests/test_api_orders_seats.py::test_parallel_same_seat_exactly_one_wins` (giai đoạn 4) | không bán quá sức chứa, không bán trùng ghế |

## Lệnh chạy

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_cancel_concurrency.py tests/test_withdrawal_concurrency.py \
  tests/test_api_admin_withdrawals.py tests/test_api_withdrawals.py tests/test_api_org_cancel.py -v
```

Kết quả lần chạy toàn bộ gần nhất (2026-11-08): `pytest -q` → **633 passed**.
