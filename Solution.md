# Solution — Day 12: Cloud Infrastructure & Deployment

Đáp án các bài codelab **1 → 5**. Mỗi section đã được chạy & verify thật bằng `uv` (chi tiết trong từng `DISCUSSION.md`).

> Lưu ý môi trường (Windows): console mặc định cp1252 làm `print()` tiếng Việt lỗi — chạy app cần `$env:PYTHONIOENCODING="utf-8"`. Các script test đều tự ép UTF-8 stdout.

---

## Codelab 1 — Localhost → Production (12-Factor)

**Đã làm:** chạy `develop/` (hardcode secret, không health check — anti-pattern) và `production/` (config từ env, `/health` `/ready` `/metrics`, graceful shutdown, fail-fast khi thiếu `AGENT_API_KEY` ở production). Verify: develop 401-free nhưng lộ secret qua log; production đọc env, fail-fast đúng.

**Câu hỏi thảo luận:**

1. **Push API key hardcode lên GitHub public?** Bot quét nhặt key trong vài phút → bill khổng lồ/truy cập trái phép. Xoá commit **không đủ** (đã nằm trong git history + bị clone/cache) → phải **revoke & rotate ngay**, xoá khỏi history (BFG), điều tra. Đây là lý do dùng env var + secret manager + `.gitignore` cho `.env`.

2. **Stateless quan trọng khi scale?** Không giữ state trong RAM instance → bất kỳ instance nào cũng xử lý được mọi request → scale ngang tự do, không mất data, không cần sticky session. State đẩy ra Redis/DB. (Demo chi tiết ở codelab 5.)

3. **"dev/prod parity" trong thực tế?** Giữ dev giống prod: pin version thư viện (`requirements.txt`), dùng chung 1 Docker image, cùng loại backing service (đừng SQLite-dev/Postgres-prod), config qua env. Chính lỗi cp1252 trên Windows là ví dụ thiếu parity.

---

## Codelab 2 — Docker

**Đã làm:** chạy `develop/` (single-stage) và `production/main.py` (multi-stage, non-root, HEALTHCHECK) bên trong image bằng `uv` (Docker không cài trên máy → verify code + review Dockerfile/compose). **Sửa:** `docker-compose.yml` build context sai → trỏ về project root; bỏ `version` deprecated; tạo `.env.local`.

**Câu hỏi thảo luận:**

1. **Vì sao `COPY requirements.txt` + `pip install` TRƯỚC `COPY . .`?** Tận dụng **Docker layer cache**. Code đổi liên tục, deps hiếm đổi. Tách riêng → sửa code không phải cài lại toàn bộ deps → build nhanh hơn nhiều.

2. **`.dockerignore` chứa gì? Vì sao `venv/` và `.env`?** Loại `__pycache__`, `venv/`, `.git/`, `.env*`, IDE/docs. `venv/` = binary theo OS host → copy vào image vô dụng + hỏng kiến trúc + nặng. `.env` = secrets → copy vào image là lộ khi push artifact. Giữ `.env.example` làm template.

3. **Agent đọc file từ disk → mount volume thế nào?** Container ephemeral → dùng volume. CLI: `-v ./data:/app/data` (bind mount) hoặc `-v mydata:/app/data` (named volume). Compose: khai báo `volumes:`. Bind mount cho dev, named volume cho data bền; `:ro` nếu chỉ đọc; lưu ý quyền ghi cho non-root user.

---

## Codelab 3 — Cloud Deployment Options

**Đã làm:** chạy & verify app Railway và Render (đúng `startCommand`), validate syntax `railway.toml` / `render.yaml` / `cloudbuild.yaml` / `service.yaml`. **Sửa/bổ sung:** tạo `render/app.py` + `requirements.txt` + `utils/` (render.yaml gọi nhưng thiếu), thêm `railway/Procfile`.

**Câu hỏi thảo luận:**

1. **Vì sao serverless (Lambda) không phải lúc nào cũng tốt cho AI agent?** Cold start nặng (load model/SDK mỗi lần), giới hạn thời gian (Lambda 15p, API Gateway timeout 29s) → LLM chậm/multi-step/streaming dễ vượt; stateless ép buộc + khó giữ connection; khó self-host model; chi phí lật ngược khi traffic cao. → Container hợp hơn cho agent.

2. **"Cold start" là gì? Ảnh hưởng UX?** Độ trễ khi platform khởi tạo instance mới từ 0 (pull image → boot → load model) trước khi phục vụ. Xảy ra khi scale-to-zero/instance đầu. UX: request "xui" chờ vài giây, trải nghiệm không nhất quán → user bỏ đi. Giảm bằng `min-instances=1`, readiness probe, image nhỏ, startup gọn.

3. **Khi nào upgrade Railway → Cloud Run?** Khi cần: kiểm soát scaling/cold start chi tiết, CI/CD nghiêm túc (build→test→deploy, rollback, canary), secrets cấp doanh nghiệp (Secret Manager/IAM), ở trong hệ sinh thái GCP, compliance/region/SLA, traffic lớn ổn định. Cứ ở Railway khi đang MVP/demo, team nhỏ, traffic chưa lớn. Nguyên tắc: chuyển khi chi phí thiếu kiểm soát > chi phí vận hành Cloud Run.

---

## Codelab 4 — API Gateway & Security

**Đã làm:** chạy `develop/` (API Key: thiếu→401, sai→403, đúng→200) và `production/` (JWT + rate limit + cost guard). **Sửa bug thật:** `production/app.py` dùng `response.headers.pop("server")` — Starlette `MutableHeaders` **không có** `.pop()` → middleware crash mọi request (500). Đổi sang `del` có kiểm tra. **Tạo:** `test_auth.py`, `test_advanced.py`. **Thêm demo:** `demo.html` + CORS cho develop app.

**Câu hỏi thảo luận:**

1. **API Key vs JWT vs OAuth2?** API Key: định danh **app/client**, static, đơn giản → internal/B2B/MVP. JWT: định danh **user**+role, stateless, có expiry, tự verify → app có user/role. OAuth2/OIDC: "Login with Google", delegated access, scope → consumer-facing. Quy tắc: máy↔máy → API Key; user+role tự quản → JWT; login bên thứ 3 → OAuth2.

2. **Rate limit bao nhiêu req/phút?** Không có số vàng — LLM đắt + chậm nên đặt thấp (lab: user 10/min, admin 100/min). Phân tier, bắt đầu thấp rồi nới, **ghép nhiều tầng**: per-minute + daily quota + cost guard (kẻ tấn công đốt tiền nhanh hơn đốt request).

3. **API key bị lộ?** Phát hiện qua bất thường (spike/budget, secret scanning). Xử lý: **revoke/rotate ngay** → phát key mới → điều tra log → xoá khỏi git history (coi như lộ vĩnh viễn) → hậu kiểm (rotation, scope hẹp, secret manager, không log key).

---

## Codelab 5 — Scaling & Reliability

**Đã làm:** chạy `develop/` (health/ready/graceful shutdown) và `production/` (stateless chat, Redis fallback in-memory). **Sửa bug thật:** `production/app.py` dùng `uvicorn.run(app, reload=True)` — `reload=True` cần **import string** "app:app" → server không start. Đã sửa. **Bổ sung:** tạo `Dockerfile` + `requirements.txt` + `.env.local` + `README.md` (section thiếu); sửa compose dockerfile path. **Demo:** `demo.html` + `auto_demo.py` (tự chạy 2 instance, minh hoạ session đứt khi in-memory).

**Câu hỏi thảo luận:**

1. **Liveness fail → restart, readiness fail → ngừng route?** Liveness "còn sống?": fail = hỏng không tự hồi → restart là cách duy nhất. Readiness "sẵn sàng?": fail thường tạm thời tự hồi (đang load/dependency gián đoạn/shutdown) → restart phản tác dụng, chỉ cần ngừng đẩy traffic. Hệ quả: `/health` phải nhẹ, đừng fail vì dependency tạm gián đoạn (kẻo restart loop).

2. **History trong biến global → hỏng gì khi scale 3 instance?** Mỗi instance RAM riêng → turn 1 vào instance A, turn 2 round-robin sang B → B không thấy history → mất ngữ cảnh. Restart/scale-down mất sạch. → Phải stateless + Redis chung (đã demo bằng `auto_demo.py`: in-memory thì session bị xé đôi giữa A và B).

3. **Redis chết → 503 hay degraded?** Tuỳ vai trò: Redis là **nguồn sự thật bắt buộc** (mất → sai/không an toàn) → **503** (readiness fail). Redis chỉ là **cache** → **degraded** (fallback, vẫn 200 + alert). Nguyên tắc **fail-safe**: sai/mất kiểm soát → từ chối; chỉ chậm → degraded. Production: chạy Redis HA.

---

## Codelab 6 — Project (Lab Assignment)

Thay project mẫu trong `06-lab-complete/` bằng agent nhóm **VinWonders AI Scheduler** (Day06) và productionize. Chi tiết: xem [06-lab-complete/README.md](06-lab-complete/README.md).
