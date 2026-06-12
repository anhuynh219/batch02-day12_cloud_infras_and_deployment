# Lab 12 — Complete Production Agent: VinWonders AI Scheduler

Project nhóm (Day 06) được **productionize** theo toàn bộ concept Day 12.
Trợ lý AI lập lịch vui chơi VinWonders Phú Quốc (React + **Gemini** + Leaflet), đóng gói thành **1 service deploy được**.

> 🔗 **API / Public URL (Railway):** https://lab12-production-40a3.up.railway.app/
> Health check: https://lab12-production-40a3.up.railway.app/health · Agent API: `POST https://lab12-production-40a3.up.railway.app/api/plan`
> Model: `gemini-2.5-flash` · Deploy: Railway (Dockerfile)

---

## ✅ Checklist Productionization (Day 12)

- [x] Config từ environment variables (12-factor) — [`server/config.ts`](server/config.ts) + fail-fast validate
- [x] Structured JSON logging — [`server/logger.ts`](server/logger.ts)
- [x] Health check (`GET /health`) + Readiness (`GET /ready`) + `GET /metrics`
- [x] API Key auth (tùy chọn, bật khi đặt `AGENT_API_KEY`) — [`server/guards.ts`](server/guards.ts)
- [x] Rate limiting (per IP, sliding window) + Cost guard (budget gọi LLM/ngày)
- [x] Security headers + CORS từ env
- [x] Graceful shutdown (SIGTERM/SIGINT)
- [x] Dockerfile multi-stage, non-root, HEALTHCHECK
- [x] Deploy config: Railway (`railway.toml`) + Render (`render.yaml`)
- [x] `.dockerignore` + `.env.example` (không commit secret)

**Luồng bảo vệ:** `Request → Security headers → Log → Rate limit (429) → API key (401) → Cost guard (503) → Agent → 200`

---

## Cấu trúc

```
06-lab-complete/
├── server/                 # AGENT BACKEND (đã productionize)
│   ├── index.ts            # wire mọi thứ + endpoints + graceful shutdown
│   ├── config.ts           # 12-factor config + validate
│   ├── logger.ts           # structured JSON logging
│   ├── guards.ts           # security headers, rate limit, api key, cost guard
│   ├── gemini.ts           # gọi Gemini (structured output)
│   └── SYSTEM_PROMPT.md     # prompt + chống prompt-injection
├── src/                    # Frontend React (engine lịch + bản đồ Leaflet)
├── public/                 # geojson bản đồ, assets
├── Dockerfile              # multi-stage, build frontend + chạy server
├── docker-compose.yml      # chạy local 1 container
├── railway.toml / render.yaml
├── .dockerignore / .env.example
└── package.json
```

**Kiến trúc hybrid:** Gemini hiểu ngôn ngữ tự nhiên + chọn trò chơi bằng `id` từ dataset (không tự tính giờ); `src/engine/scheduleEngine.ts` tính giờ + buffer di chuyển + cảnh báo; `src/lib/router.ts` chạy Dijkstra trên đồ thị đường đi thật để vẽ route.

---

## Chạy local

### Cách A — dev (web + api riêng, hot reload)
```bash
npm install
cp .env.example .env          # điền GEMINI_API_KEY (key bắt đầu AIza)
npm run dev                   # web :5173 (proxy /api → :8787)
```

### Cách B — production build (1 server serve cả web + api)
```bash
npm install
npm run build                 # → dist/
GEMINI_API_KEY=AIza... ENVIRONMENT=production npm run start
# → http://localhost:8787   (web + /api/plan + /health)
```

### Cách C — Docker
```bash
cp .env.example .env.local    # điền GEMINI_API_KEY
docker compose up --build
curl http://localhost:8787/health
```

### Kiểm tra nhanh (không cần Gemini key)
```bash
curl http://localhost:8787/health     # 200, liveness
curl http://localhost:8787/ready      # 200, readiness
curl http://localhost:8787/metrics    # uptime + cost guard
# /api/plan không có GEMINI_API_KEY → trả 'clarify' (graceful fallback, không crash)
```

---

## Endpoints

| Method | Path | Mô tả | Bảo vệ |
|--------|------|-------|--------|
| POST | `/api/plan` | Lập/sửa lịch (Gemini) | rate limit + (optional) API key + cost guard |
| GET | `/health` | Liveness probe | public |
| GET | `/ready` | Readiness probe | public |
| GET | `/metrics` | Uptime + cost guard | public |

`POST /api/plan` body: `{ "messages": [{"role":"user","text":"..."}], "itinerarySummary": "", "persona": "" }`

---

## Biến môi trường

| Biến | Mặc định | Ghi chú |
|------|----------|---------|
| `GEMINI_API_KEY` | — | **Bắt buộc ở production** (fail-fast nếu thiếu) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | |
| `PORT` | `8787` | Railway/Render tự inject |
| `ENVIRONMENT` | `development` | `production` → bật fail-fast |
| `AGENT_API_KEY` | *(trống)* | đặt → bắt buộc header `X-API-Key` |
| `ALLOWED_ORIGINS` | `*` | CORS, dấu phẩy phân cách |
| `RATE_LIMIT_PER_MINUTE` | `20` | |
| `DAILY_CALL_BUDGET` | `1000` | số lần gọi LLM tối đa/ngày |

---

## Deploy

### Railway (nhanh nhất)
```bash
npm i -g @railway/cli
railway login
railway init
railway variables set GEMINI_API_KEY=AIza... ENVIRONMENT=production
railway up
railway domain          # ← nhận public URL, dán vào đầu README
```

### Render (Blueprint)
1. Push repo lên GitHub.
2. Render Dashboard → New → Blueprint → connect repo (đọc `render.yaml`).
3. Nhập secret `GEMINI_API_KEY` (sync:false) → Deploy → nhận URL.

> ⚠️ Deploy thật cần **GEMINI_API_KEY** của bạn + tài khoản Railway/Render. Sau khi `railway up` / Render deploy xong, dán URL vào ô **API / Public URL** ở đầu file này.

---

## Demo 4 paths (cần GEMINI_API_KEY thật)

- **Happy:** "Đoàn 4 người có bé 6 tuổi, đến 9h về 15h, thích nhẹ nhàng, muốn xem show, ăn trưa ~12h." → AI lập lịch, timeline + route.
- **Low-confidence:** "Có trò nào vui không?" → AI hỏi lại.
- **Failure:** "Mình chỉ rảnh 19:00–19:30, chơi tàu lượn Zeus và xem show Once." → cảnh báo ⚠ (đóng cửa/không kịp/quá giờ).
- **Correction:** khoá 🔒 1 mục rồi xoá mục khác → lịch + route tính lại.

## Test
```bash
npm run test
```
