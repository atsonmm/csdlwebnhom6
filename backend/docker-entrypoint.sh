#!/bin/sh
# Khởi động container backend:
#   1) chờ CSDL (máy ảo DB có thể khởi động chậm hơn) rồi `alembic upgrade head` — migration có phiên bản;
#   2) nạp danh mục (upsert, chạy lại an toàn) + tài khoản quản trị nếu SEED_CATALOG=1;
#   3) chạy uvicorn sau reverse proxy (nginx của máy ảo frontend).
set -e

tries=0
until python -m alembic upgrade head; do
  tries=$((tries + 1))
  if [ "$tries" -ge 30 ]; then
    echo "[entrypoint] Không kết nối / nâng cấp được CSDL sau 30 lần thử — kiểm tra DATABASE_URL" >&2
    exit 1
  fi
  echo "[entrypoint] CSDL chưa sẵn sàng, thử lại sau 2 giây ($tries/30)..."
  sleep 2
done

if [ "${SEED_CATALOG:-1}" = "1" ]; then
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*" --workers "${UVICORN_WORKERS:-2}"
