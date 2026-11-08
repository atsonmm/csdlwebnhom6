"""Kiểm thử đồng thời bằng 2 KẾT NỐI CSDL THẬT (học phần: "gọi lần lượt hai lần không được tính").

race(engine, fn_a, fn_b, module=..., hold=0.3):
- chạy fn_a(session) và fn_b(session) trên 2 luồng, mỗi luồng một Session(engine) = một kết nối riêng;
- cùng xuất phát qua threading.Barrier;
- service gọi `module._after_lock()` ngay sau khi giành được khoá dòng (SELECT … FOR UPDATE): bên đến TRƯỚC
  ngủ `hold` giây trong lúc giữ khoá, nên bên kia chắc chắn bị chặn ở câu khoá cho tới khi bên trước commit;
- trả về [Outcome(a), Outcome(b)] với kết quả (giá trị trả về hoặc mã HTTP lỗi) và thời gian chạy.
"""
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session


@dataclass
class Outcome:
    ok: bool
    value: Any  # giá trị trả về khi ok, mã HTTP khi lỗi
    detail: str | None
    elapsed: float


def race(engine, fn_a: Callable[[Session], Any], fn_b: Callable[[Session], Any], *, module, hold: float = 0.3,
         monkeypatch) -> list[Outcome]:
    first = threading.Lock()
    holder: list[str] = []

    def after_lock() -> None:
        with first:
            is_first = not holder
            holder.append(threading.current_thread().name)
        if is_first:
            time.sleep(hold)  # giữ khoá → bên kia phải chờ

    monkeypatch.setattr(module, "_after_lock", after_lock)
    barrier = threading.Barrier(2)
    out: list[Outcome | None] = [None, None]

    def run(i: int, fn) -> None:
        with Session(engine) as s:
            barrier.wait()
            t0 = time.perf_counter()
            try:
                value = fn(s)
                s.commit()
                out[i] = Outcome(True, value, None, time.perf_counter() - t0)
            except HTTPException as e:
                s.rollback()
                out[i] = Outcome(False, e.status_code, str(e.detail), time.perf_counter() - t0)

    threads = [threading.Thread(target=run, args=(i, fn), name=f"ket-noi-{i}") for i, fn in enumerate((fn_a, fn_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert all(o is not None for o in out), "một luồng không kết thúc (deadlock?)"
    return out  # type: ignore[return-value]


def winner_loser(outs: list[Outcome]) -> tuple[Outcome, Outcome]:
    oks = [o for o in outs if o.ok]
    fails = [o for o in outs if not o.ok]
    assert len(oks) == 1 and len(fails) == 1, outs
    return oks[0], fails[0]
