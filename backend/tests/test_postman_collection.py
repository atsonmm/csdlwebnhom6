"""Collection Postman là sản phẩm bàn giao của mỗi giai đoạn: mọi URL phải là {{baseUrl}}/..."""
import json
from pathlib import Path

COLLECTION = Path(__file__).resolve().parent.parent / "postman/ticketnhip.postman_collection.json"


def _requests(items):
    for it in items:
        if "item" in it:
            yield from _requests(it["item"])
        else:
            yield it


def test_every_request_url_is_relative_to_base_url():
    col = json.loads(COLLECTION.read_text(encoding="utf-8"))
    bad = [r["name"] for r in _requests(col["item"])
           if not (u := r["request"]["url"] if isinstance(r["request"]["url"], str) else r["request"]["url"]["raw"])
           .startswith("{{baseUrl}}/") or ":/" in u.removeprefix("{{baseUrl}}")]
    assert bad == []
