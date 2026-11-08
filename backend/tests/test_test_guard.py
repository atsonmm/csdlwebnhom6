import pytest

from tests.conftest import ensure_test_database


def test_guard_refuses_non_test_database():
    with pytest.raises(RuntimeError, match="_test"):
        ensure_test_database("postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip")


def test_guard_accepts_test_database():
    ensure_test_database("postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip_test")
