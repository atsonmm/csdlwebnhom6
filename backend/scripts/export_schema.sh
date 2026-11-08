#!/usr/bin/env bash
# Xuất lược đồ (không dữ liệu) của CSDL ticketnhip ra database/schema.sql — dùng cho báo cáo
set -euo pipefail
cd "$(dirname "$0")/.."
PGPASSWORD="${PGPASSWORD:-ticketnhip}" "/c/Program Files/PostgreSQL/18/bin/pg_dump.exe" \
  --schema-only --no-owner --no-privileges -h localhost -U ticketnhip ticketnhip > ../database/schema.sql
echo "Đã ghi database/schema.sql"
