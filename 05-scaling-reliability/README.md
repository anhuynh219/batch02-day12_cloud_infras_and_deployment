# Section 5 — Scaling & Reliability

## Mục tiêu học
- Health check: phân biệt **liveness** (`/health`) và **readiness** (`/ready`)
- Graceful shutdown: hoàn thành request đang xử lý trước khi tắt
- **Stateless**: vì sao agent không được giữ state trong memory khi scale
- Scale ngang: nhiều instance + Redis (shared state) + Nginx (load balancer)

---

## Ví dụ Basic — Health Check + Graceful Shutdown

```
develop/
├── app.py            # /health, /ready, graceful shutdown, in-flight tracking
├── requirements.txt  # fastapi, uvicorn, psutil
└── utils/
```

### Chạy thử
```bash
cd develop
# Windows: $env:PYTHONIOENCODING="utf-8"
uv run --with fastapi --with "uvicorn[standard]" --with psutil python app.py

curl http://localhost:8000/health   # liveness — luôn 200 khi còn sống
curl http://localhost:8000/ready    # readiness — 503 khi đang khởi động/shutdown
```

- **Liveness** fail → platform **restart** container.
- **Readiness** fail → load balancer **ngừng route** traffic (không restart).
- Graceful shutdown: nhận SIGTERM → ngừng nhận request mới → chờ in-flight xong → thoát.

---

## Ví dụ Advanced — Stateless Agent + Redis + Nginx (scale ngang)

```
production/
├── app.py              # /chat multi-turn, session lưu ở Redis (fallback in-memory)
├── requirements.txt    # + redis, pydantic
├── Dockerfile          # image stateless cho nhiều replica
├── docker-compose.yml  # 3 agent + redis + nginx
├── nginx.conf          # round-robin load balancer
├── test_stateless.py   # chứng minh session liên tục qua nhiều instance
└── utils/
```

### Vì sao phải stateless?
```
Instance 1: User A → request 1 → lưu session TRONG MEMORY của instance 1
Instance 2: User A → request 2 → instance 2 KHÔNG có session đó → BUG
✅ Giải pháp: lưu session ở Redis → mọi instance đọc được
```

### Chạy local (1 instance, không cần Docker)
```bash
cd production
# Không có Redis → tự fallback in-memory store
uv run --with fastapi --with "uvicorn[standard]" --with pydantic python app.py

# Test multi-turn (giữ session_id giữa các request)
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"question":"What is Docker?"}'
# Lấy session_id từ response, gửi kèm ở request sau
```

### Chạy full stack scale 3 instance (cần Docker)
```bash
# Từ project root
docker compose -f 05-scaling-reliability/production/docker-compose.yml up --build

# Test — quan sát "served_by" đổi instance nhưng session vẫn liên tục
python 05-scaling-reliability/production/test_stateless.py
```

> `test_stateless.py` mặc định gọi Nginx ở `http://localhost:8080`.
> Test 1 instance local: `BASE_URL=http://localhost:8000 python test_stateless.py`.

---

## Câu hỏi thảo luận
1. Vì sao liveness fail thì restart, còn readiness fail thì chỉ ngừng route traffic?
2. Nếu agent giữ conversation history trong biến global, điều gì hỏng khi scale lên 3 instance?
3. Redis chết thì sao? Agent nên trả 503 (readiness fail) hay vẫn phục vụ ở chế độ degraded?
