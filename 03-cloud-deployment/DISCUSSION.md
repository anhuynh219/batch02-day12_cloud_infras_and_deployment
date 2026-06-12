# Section 3 — Trả lời câu hỏi thảo luận

> Nguồn câu hỏi: [README.md](README.md) · gắn với context của lab (AI agent, mock LLM, các tier Railway → Cloud Run).

---

## 1. Tại sao serverless (Lambda) không phải lúc nào cũng tốt cho AI agent?

Serverless (AWS Lambda, Cloud Functions) tuyệt cho việc ngắn, stateless, traffic giật cục — nhưng AI agent lại vướng đúng những điểm yếu của nó:

- **Cold start nặng hơn nhiều.** Agent thường phải load model/tokenizer, mở connection tới vector DB, khởi tạo SDK (OpenAI/Anthropic). Mỗi lần container "ngủ dậy" phải làm lại từ đầu → trễ vài giây.
- **Giới hạn thời gian chạy.** Lambda tối đa 15 phút, API Gateway timeout mặc định **29 giây**. LLM trả lời chậm, hoặc agent multi-step (gọi tool → suy luận → gọi tiếp), hoặc **streaming token** dài rất dễ vượt timeout.
- **Stateless ép buộc + không giữ connection.** Không giữ được warm connection pool tới DB/Redis; mỗi invocation tự lo. Streaming response (SSE/WebSocket) cũng khó/đắt trên Lambda.
- **Khó với model nặng.** Giới hạn RAM/disk, không GPU (thực tế) → chỉ hợp khi gọi LLM qua API bên ngoài, không hợp self-host model.
- **Chi phí lật ngược ở traffic cao.** Serverless rẻ khi traffic thấp/thưa; khi agent bị gọi liên tục, tính theo mỗi request + GB-giây có thể **đắt hơn** một container chạy thường trú.

→ Lambda hợp với webhook, batch ngắn, glue code. Agent cần độ trễ ổn định, request dài, streaming, connection thường trú → container (Railway/Render/Cloud Run) hợp hơn. Đó cũng là lý do lab này deploy bằng **container**, không phải function.

---

## 2. "Cold start" là gì? Ảnh hưởng thế nào đến UX?

**Cold start** = độ trễ thêm vào khi platform phải **khởi tạo một instance mới từ con số 0** trước khi xử lý request: kéo image → khởi động container → chạy startup code (load model, connect DB, import thư viện) → mới sẵn sàng. So với **warm start** (instance đã chạy sẵn, trả lời ngay).

**Khi nào xảy ra:** instance đầu tiên, sau khi **scale-to-zero** (không có traffic nên platform tắt hết để tiết kiệm — Cloud Run, Lambda hay làm), hoặc lúc auto-scale tăng thêm instance.

**Ảnh hưởng UX:**
- Request "xui" rơi vào cold start chờ **vài trăm ms đến vài giây** trong khi request khác trả lời tức thì → trải nghiệm **không nhất quán**, khó debug ("lúc nhanh lúc chậm").
- Với chatbot/agent, người dùng gõ câu đầu tiên mà chờ 3–5s tưởng như bị treo → bỏ đi.
- Health check cũng dính: nếu probe gọi vào lúc đang khởi động → fail → platform tưởng chết.

**Cách giảm (đúng những gì config trong lab làm):**
- **`min-instances: 1`** — giữ ít nhất 1 instance luôn ấm, không scale-to-zero. Thấy ở [cloudbuild.yaml](production-cloud-run/cloudbuild.yaml) (`--min-instances=1`) và [service.yaml](production-cloud-run/service.yaml) (`minScale: "1"`) — comment ghi rõ "tránh cold start".
- **`startupProbe` / readiness** (`/ready`) — để platform chỉ route traffic khi đã load xong, tránh đẩy request vào instance chưa sẵn sàng.
- Image nhỏ (multi-stage `slim` ở section 02) → pull & boot nhanh hơn.
- Startup gọn: lazy-load thứ nặng, đừng block toàn bộ ở `lifespan`.

**Đánh đổi:** `min-instances=1` = trả tiền 24/7 cho 1 instance để đổi lấy độ trễ ổn định.

---

## 3. Khi nào nên upgrade từ Railway lên Cloud Run?

Bảng tier trong README: Railway/Render là **Tier 1 (MVP, demo, học)**, Cloud Run là **Tier 2 (production)**. Nên nâng cấp khi chạm các ngưỡng sau.

**Nâng lên Cloud Run khi:**
- **Cần kiểm soát scaling & cold start chi tiết** — đặt `min/maxScale`, `containerConcurrency`, CPU/memory cụ thể (xem service.yaml). Railway scaling đơn giản hơn nhiều.
- **Cần CI/CD nghiêm túc** — pipeline test → build → push → deploy tự động (cloudbuild.yaml), rollback theo revision, traffic splitting (canary/blue-green).
- **Bảo mật/secrets cấp doanh nghiệp** — tích hợp **Secret Manager**, IAM, VPC, service account (service.yaml dùng `secretKeyRef`).
- **Đã ở trong hệ sinh thái GCP** — gần BigQuery, Pub/Sub, Vertex AI, Cloud SQL → giảm latency và phức tạp.
- **Cần compliance / region cụ thể / SLA**, traffic lớn và ổn định, cần tối ưu chi phí ở quy mô.
- **Scale-to-zero thật sự** cho workload thưa nhưng vẫn muốn cấu hình production-grade.

**Cứ ở lại Railway/Render khi:**
- Đang MVP, demo, hackathon, dạy học — ưu tiên **deploy < 5–10 phút**, không muốn config hạ tầng.
- Team nhỏ, không có DevOps; muốn `git push` là tự deploy.
- Traffic chưa lớn, chưa cần tinh chỉnh scaling/secrets phức tạp.

**Một câu để nhớ:** chuyển khi *chi phí của việc thiếu kiểm soát (scaling, CI/CD, secrets, compliance) lớn hơn chi phí vận hành Cloud Run*. Đừng nâng cấp sớm chỉ vì "nghe production hơn" — thêm phức tạp mà chưa cần thì phản tác dụng. Đường tiến hoá tự nhiên: **Railway để validate ý tưởng → Cloud Run khi đã có người dùng thật và cần độ tin cậy**.
