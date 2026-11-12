"""Migration 0019 — ràng buộc của bảng câu hỏi khi đặt vé (event_questions, order_answers)"""
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import Event
from app.models.questions import EventQuestion, OrderAnswer
from app.models.sales import Order


def question(db, event_id, qid="q1", **over):
    row = EventQuestion(**({"event_id": event_id, "id": qid, "kind": "text", "label": "Bạn biết sự kiện qua đâu?",
                            "sort_order": 0} | over))
    db.add(row)
    db.flush()
    return row


def test_question_defaults(db, make_show_tier):
    e, _s, _t = make_show_tier
    q = question(db, e.id)
    db.refresh(q)
    assert q.required is True and q.help is None and q.options is None


def test_unknown_kind_rejected(db, make_show_tier):
    e, _s, _t = make_show_tier
    with pytest.raises(IntegrityError, match="ck_event_questions_kind"):
        question(db, e.id, kind="essay")


def test_choice_needs_options_array(db, make_show_tier):
    e, _s, _t = make_show_tier
    with pytest.raises(IntegrityError, match="ck_event_questions_options"):
        question(db, e.id, kind="choice")
    db.rollback()


def test_choice_with_options_ok(db, make_show_tier):
    e, _s, _t = make_show_tier
    assert question(db, e.id, kind="choice", options=["Facebook", "Bạn bè"]).options == ["Facebook", "Bạn bè"]


def test_question_removed_with_its_event(db, make_show_tier):
    e, _s, _t = make_show_tier
    question(db, e.id)
    db.execute(delete(Event).where(Event.id == e.id))  # huỷ sự kiện chưa có đơn → xoá hẳn, câu hỏi đi theo
    assert db.scalar(select(EventQuestion.id).where(EventQuestion.event_id == e.id)) is None


def test_answered_question_cannot_be_deleted(db, make_order):
    q = question(db, make_order.event_id)
    db.add(OrderAnswer(order_id=make_order.id, event_id=make_order.event_id, question_id=q.id, value="Facebook",
                       label_snapshot=q.label))
    db.flush()
    with pytest.raises(IntegrityError, match="fk_order_answers_question"):
        db.execute(delete(EventQuestion).where(EventQuestion.event_id == q.event_id, EventQuestion.id == q.id))
    db.rollback()


def test_answer_event_must_match_its_order(db, make_order):
    q = question(db, make_order.event_id)
    db.add(OrderAnswer(order_id=make_order.id, event_id=make_order.event_id + 1, question_id=q.id, value="x",
                       label_snapshot=q.label))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_answers_removed_with_their_order(db, make_order):
    q = question(db, make_order.event_id)
    db.add(OrderAnswer(order_id=make_order.id, event_id=make_order.event_id, question_id=q.id, value="x",
                       label_snapshot=q.label))
    db.flush()
    db.execute(delete(Order).where(Order.id == make_order.id))
    assert db.scalar(select(OrderAnswer.order_id).where(OrderAnswer.order_id == make_order.id)) is None


# ------------------------------------------------------------------ loại 'multi' (migration 0020)
def test_multi_question_needs_options_array(db, make_show_tier):
    e, _s, _t = make_show_tier
    with pytest.raises(IntegrityError, match="ck_event_questions_options"):
        question(db, e.id, kind="multi")
    db.rollback()


def test_multi_question_with_options_ok(db, make_show_tier):
    e, _s, _t = make_show_tier
    assert question(db, e.id, kind="multi", options=["Nhạc", "Kịch"]).kind == "multi"
