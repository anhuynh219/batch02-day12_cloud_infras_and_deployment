# Section 1 — Trả lời câu hỏi thảo luận (Localhost → Production)

> Nguồn: [README.md](README.md)

---

## 1. Điều gì xảy ra nếu bạn push code với API key hardcode lên GitHub public?

Key bị lộ **ngay lập tức và vĩnh viễn**:

- **Bot quét GitHub liên tục** (theo giây–phút) tìm secret pattern (`sk-...`, AWS key, v.v.). Key bị nhặt trong **vài phút**.
- Hậu quả: lạm dụng API → **bill khổng lồ** (nhất là LLM/cloud), truy cập trái phép data, abuse hạ tầng (đào coin, gửi spam).
- **Xoá commit không đủ.** Key đã nằm trong **git history** và có thể đã bị clone/fork/cache/đánh chỉ mục.

**Phải làm:** coi như đã lộ → **revoke & rotate ngay**, xoá khỏi history (BFG/git-filter-repo), điều tra log thiệt hại.

→ Đây chính là lý do section 1 dạy: config từ **env var**, dùng **secret manager**, `.gitignore` cho `.env`, chỉ commit `.env.example`. (`develop/app.py` cố tình hardcode để minh hoạ cái sai.)

---

## 2. Tại sao stateless quan trọng khi scale?

**Stateless** = không giữ state trong RAM của instance → **bất kỳ instance nào cũng xử lý được bất kỳ request nào**.

- Cho phép **scale ngang** tự do: thêm/bớt instance, restart, autoscale — mà **không mất dữ liệu user**, không cần sticky session, không trả lời sai ngữ cảnh.
- State đẩy ra ngoài: **Redis/DB** (session, history, cache).
- **Stateful** (giữ state trong biến global) → **vỡ** khi load balancer route request sang instance khác.

→ Xem demo chi tiết ở section 5 (`served_by` đổi instance nhưng session vẫn liên tục nhờ Redis).

---

## 3. 12-factor nói "dev/prod parity" — nghĩa là gì trong thực tế?

Giữ môi trường **dev càng giống prod càng tốt** để giảm bug "chạy trên máy tôi mà". Cụ thể, thu hẹp 3 khoảng cách:

- **Công cụ/runtime**: cùng phiên bản ngôn ngữ + thư viện (**pin** trong `requirements.txt`), cùng OS/runtime (dùng chung **1 Docker image** cho cả dev lẫn prod).
- **Backing services**: dùng **cùng loại** service từ dev (Postgres/Redis thật), đừng SQLite ở dev rồi Postgres ở prod.
- **Cấu hình**: cùng cách (env var), khác giá trị.
- **Thời gian & nhân sự**: deploy thường xuyên (khoảng cách dev→prod ngắn), dev tự deploy.

→ Lab này đạt parity bằng **Docker + config-from-env + pinned deps**.
Trớ trêu: chính lỗi **cp1252 trên Windows console** lúc chạy local là một ví dụ **thiếu parity** (encoding console khác Linux) — fix bằng `PYTHONIOENCODING=utf-8`.
