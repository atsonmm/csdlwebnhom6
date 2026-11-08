"""Phục vụ bản build React (frontend/dist) cùng cổng với API khi chạy thật"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def install_spa(app: FastAPI, dist: Path) -> None:
    """Chạy thật: phục vụ bản build React (dist/) cùng cổng với API.
    - /api/... không khớp route nào → 404 JSON như cũ
    - file có thật trong dist (assets, favicon…) → trả file
    - đường dẫn có đuôi file mà không tồn tại → 404 (không trả index.html cho file hỏng)
    - còn lại (/su-kien/abc, /ban-to-chuc…) → index.html để React Router xử lý"""
    root = dist.resolve()
    index = root / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise StarletteHTTPException(404)
        target = (root / full_path).resolve()
        if target.is_relative_to(root) and target.is_file():
            return FileResponse(target)
        if "." in full_path.rsplit("/", 1)[-1]:
            raise StarletteHTTPException(404)
        return FileResponse(index, media_type="text/html")
