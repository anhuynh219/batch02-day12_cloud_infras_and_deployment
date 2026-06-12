# ============================================================
# Stateless Agent — image cho scaling demo (3 replicas + Redis + Nginx)
#
# Build từ PROJECT ROOT (vì COPY dùng path từ root):
#   docker build -f 05-scaling-reliability/production/Dockerfile -t agent-stateless .
# Hoặc qua compose:
#   docker compose -f 05-scaling-reliability/production/docker-compose.yml up
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Cài deps trước để tận dụng layer cache
COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code
COPY 05-scaling-reliability/production/app.py .

# Mock utils (từ project root)
RUN mkdir -p utils
COPY utils/mock_llm.py utils/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Stateless → chạy nhiều instance đằng sau Nginx, state nằm ở Redis
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
