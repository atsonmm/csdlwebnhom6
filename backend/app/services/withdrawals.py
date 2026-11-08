"""Rút tiền của Ban tổ chức (Task E1) — số dư và yêu cầu rút; Admin duyệt ở Task E2.

Số dư (theo từng sự kiện của BTC, phí sàn tính riêng từng sự kiện bằng manage.fee_of):
- settledNet: thực nhận của các sự kiện ĐÃ DIỄN (phase 'ended') — chỉ phần này rút được;
- held: thực nhận của các sự kiện chưa diễn (còn có thể bị huỷ → hoàn tiền), đang tạm giữ;
- available = settledNet − pending − paid (sự kiện đã diễn không huỷ được nên không bao giờ âm).
"""
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.catalog import Event, Show
from app.models.payouts import Withdrawal
from app.models.sales import Order
from app.models.users import Organizer
from app.services import manage, sql_queries
from app.utils.timefmt import iso_vn

MIN_AMOUNT = 50_000
NOT_ENOUGH = "Số dư khả dụng không đủ"
AMOUNT_MSG = "Số tiền rút tối thiểu 50.000 ₫"
BANK_MSG = "Vui lòng nhập tên ngân hàng"
ACCOUNT_NO_MSG = "Số tài khoản chỉ gồm 6–20 chữ số"
ACCOUNT_NAME_MSG = "Vui lòng nhập tên chủ tài khoản"
ACCOUNT_NO_RE = re.compile(r"[0-9]{6,20}")  # chỉ chữ số ASCII


def _after_lock() -> None:
    """Móc chạy ngay sau khi khoá dòng organizers — mặc định không làm gì; test đồng thời dùng để giữ khoá"""


def _zero() -> dict:
    return {"settledNet": 0, "held": 0, "pending": 0, "paid": 0, "available": 0}


def balances(db: Session, organizer_ids: list[int] | None = None) -> dict[int, dict]:
    """Số dư của nhiều BTC một lượt (None = mọi BTC) — MỘT truy vấn Q8 withdrawal_balance.sql (CTE + SUM FILTER)"""
    out: dict[int, dict] = {oid: _zero() for oid in (organizer_ids or [])}
    for r in sql_queries.run(db, "withdrawal_balance", orgs=list(organizer_ids) if organizer_ids is not None else None,
                             fee_rate=manage.FEE_RATE, now=manage.now_utc()):
        out[r["organizer_id"]] = {"settledNet": int(r["settled"]), "held": int(r["held"]), "pending": int(r["pending"]),
                                  "paid": int(r["paid"]), "available": 0}
    for b in out.values():
        b["available"] = max(b["settledNet"] - b["pending"] - b["paid"], 0)
    return out


def balance(db: Session, organizer_id: int) -> dict:
    return balances(db, [organizer_id])[organizer_id]


def to_json(w: Withdrawal, org_name: str | None = None) -> dict:
    out = {"id": w.id, "amount": w.amount, "bankName": w.bank_name, "accountNo": w.account_no,
           "accountName": w.account_name, "status": w.status, "note": w.note,
           "createdAt": iso_vn(w.created_at), "processedAt": iso_vn(w.processed_at)}
    if org_name is not None:
        out["orgName"] = org_name
    return out


def list_for(db: Session, organizer_id: int) -> list[Withdrawal]:
    return list(db.scalars(select(Withdrawal).where(Withdrawal.organizer_id == organizer_id)
                           .order_by(Withdrawal.created_at.desc(), Withdrawal.id.desc())))


def _text(v: Any, lo: int, hi: int) -> str | None:
    if not isinstance(v, str):
        return None
    s = " ".join(v.split())
    return s if lo <= len(s) <= hi else None


def _validate(body: dict) -> dict:
    amount = manage._int(body.get("amount"))
    if amount is None or amount < MIN_AMOUNT:
        raise HTTPException(400, AMOUNT_MSG)
    bank = _text(body.get("bankName"), 2, 60)
    if bank is None:
        raise HTTPException(400, BANK_MSG)
    acc_no = body.get("accountNo")
    if not isinstance(acc_no, str) or not ACCOUNT_NO_RE.fullmatch(acc_no.strip()):
        raise HTTPException(400, ACCOUNT_NO_MSG)
    acc_name = _text(body.get("accountName"), 2, 60)
    if acc_name is None:
        raise HTTPException(400, ACCOUNT_NAME_MSG)
    return {"amount": amount, "bank_name": bank, "account_no": acc_no.strip(), "account_name": acc_name}


def request(db: Session, organizer_id: int, body: Any) -> Withdrawal:
    """Tạo yêu cầu rút. Khoá dòng organizers FOR UPDATE TRƯỚC khi tính số dư: hai yêu cầu của cùng BTC xếp hàng,
    bên sau thấy khoản 'pending' của bên trước → không rút quá số dư. Người gọi commit (lỗi → rollback)."""
    data = body if isinstance(body, dict) else body.model_dump()
    v = _validate(data)
    locked = db.scalar(select(Organizer.user_id).where(Organizer.user_id == organizer_id).with_for_update())
    if locked is None:
        raise HTTPException(404, "Không tìm thấy Ban tổ chức")
    _after_lock()
    if v["amount"] > balance(db, organizer_id)["available"]:
        raise HTTPException(409, NOT_ENOUGH)
    w = Withdrawal(organizer_id=organizer_id, **v)
    db.add(w)
    db.flush()
    db.refresh(w)
    return w


# ---------------------------------------------------------------- Admin duyệt (Task E2)
STATUSES = ("pending", "paid", "rejected")
NOT_FOUND = "Không tìm thấy yêu cầu rút tiền"
ALREADY_DONE = "Yêu cầu này đã được xử lý"
NOTE_MSG = "Vui lòng nhập lý do từ chối (3–300 ký tự)"
ID_RE = re.compile(r"[0-9]{1,10}")


def admin_list(db: Session, status: str) -> list[dict]:
    """Yêu cầu rút tiền toàn sàn kèm tên BTC và số dư khả dụng hiện tại của BTC đó (để Admin đối chiếu).
    Chờ xử lý: cũ trước (hàng đợi); còn lại: mới trước."""
    if status not in (*STATUSES, "all"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    q = select(Withdrawal, Organizer.org_name).join(Organizer, Organizer.user_id == Withdrawal.organizer_id)
    if status != "all":
        q = q.where(Withdrawal.status == status)
    q = q.order_by(Withdrawal.created_at, Withdrawal.id) if status == "pending" else         q.order_by(Withdrawal.created_at.desc(), Withdrawal.id.desc())
    rows = db.execute(q).all()
    bal = balances(db, list({w.organizer_id for w, _ in rows})) if rows else {}
    return [to_json(w, name) | {"organizerId": w.organizer_id, "orgAvailable": bal[w.organizer_id]["available"]}
            for w, name in rows]


def parse_id(raw: str) -> int:
    if not ID_RE.fullmatch(raw) or int(raw) > 2_147_483_647:
        raise HTTPException(404, NOT_FOUND)
    return int(raw)


def decide(db: Session, admin: Any, withdrawal_id: int, decision: Any, note: Any) -> dict:
    """Đánh dấu đã chuyển / từ chối — MỘT câu UPDATE có điều kiện status = 'pending' (khoá dòng tới khi commit):
    hai Admin bấm cùng lúc thì bên sau chờ khoá, đọc lại thấy không còn 'pending' → 409. Người gọi commit."""
    if decision not in ("paid", "rejected"):
        raise HTTPException(400, "Quyết định không hợp lệ")
    text = " ".join(note.split()) if isinstance(note, str) else ""
    if decision == "rejected" and not 3 <= len(text) <= 300:
        raise HTTPException(400, NOTE_MSG)
    w = db.scalar(update(Withdrawal).where(Withdrawal.id == withdrawal_id, Withdrawal.status == "pending")
                  .values(status=decision, note=text[:300] or None, processed_at=func.now(), processed_by=admin.id)
                  .returning(Withdrawal).execution_options(populate_existing=True))
    if w is None:
        exists = db.scalar(select(Withdrawal.id).where(Withdrawal.id == withdrawal_id))
        raise HTTPException(409 if exists else 404, ALREADY_DONE if exists else NOT_FOUND)
    _after_lock()
    org_name = db.scalar(select(Organizer.org_name).where(Organizer.user_id == w.organizer_id))
    return {"withdrawal": to_json(w, org_name)}
