# Máy ảo BACKEND — FastAPI + Alembic (Python 3.14). Build: docker build -t ticketnhip-backend ./backend
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

# Cài thư viện trước (tận dụng cache khi chỉ đổi mã nguồn)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Chạy bằng người dùng thường, không dùng root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
