# Section 5 — Trả lời câu hỏi thảo luận (Scaling & Reliability)

> Nguồn: [README.md](README.md)

---

## 1. Vì sao liveness fail thì restart, còn readiness fail thì chỉ ngừng route traffic?

- **Liveness** (`/health`) = "process còn sống không?". Fail nghĩa là agent đã **hỏng/treo không tự hồi phục** → cách duy nhất cứu là **restart** container (giết & tạo lại).
- **Readiness** (`/ready`) = "sẵn sàng nhận request chưa?". Fail thường là **tạm thời và tự hồi**: đang khởi động, đang load model, dependency tạm gián đoạn, đang shutdown, hoặc quá tải. Instance vẫn sống. Restart lúc này **phản tác dụng** (mất thời gian boot, dễ restart loop). Việc đúng là **ngừng đẩy traffic** vào nó cho tới khi ready lại.

**Hệ quả thiết kế:** tách 2 probe rõ ràng.
- `/health` phải **nhẹ** và chỉ fail khi thật sự hỏng — **đừng** cho nó fail vì dependency tạm gián đoạn, kẻo bị restart oan/loop.
- `/ready` mới phản ánh khả năng phục vụ (vd ping Redis như `production/app.py`).
- Nhầm lẫn 2 cái = restart oan, hoặc route request vào instance chưa sẵn sàng → lỗi cho user.

---

## 2. Nếu agent giữ conversation history trong biến global, điều gì hỏng khi scale lên 3 instance?

Mỗi instance có vùng nhớ **riêng**. Kịch bản vỡ:
- User A turn 1 → load balancer route vào **instance 1** → history lưu ở RAM instance 1.
- Turn 2 → round-robin sang **instance 2** → instance 2 **không thấy** history → agent mất ngữ cảnh, trả lời rời rạc như gặp người lạ.

Thêm các hỏng hóc:
- Instance restart / scale-down → **mất sạch** history trong RAM.
- Không share được giữa các instance; **sticky session** chỉ chữa cháy (gây lệch tải, vẫn mất khi instance đó chết).

→ Đây chính là demo của section: **stateless + lưu state ở Redis** → instance nào cũng đọc được session (`served_by` đổi instance nhưng history vẫn liên tục). **Biến global = stateful = vỡ khi scale ngang.**

---

## 3. Redis chết thì sao? Agent nên trả 503 (readiness fail) hay vẫn phục vụ ở chế độ degraded?

Tuỳ **vai trò của Redis**:

- Redis là **nguồn sự thật bắt buộc** (mất nó → agent trả lời sai ngữ cảnh, hoặc rate-limit/budget mất an toàn) → nên **readiness fail (503)**, load balancer ngừng route, chờ Redis hồi. Thà từ chối còn hơn phục vụ sai/không an toàn. (`production/app.py` `/ready` ping Redis → 503 nếu fail.)
- Redis chỉ là **cache/tăng tốc** (mất vẫn chạy đúng, chỉ chậm/mất lịch sử cũ) → **degraded**: fallback in-memory hoặc bỏ cache, vẫn trả 200, log cảnh báo. (app.py có sẵn fallback in-memory khi không có Redis.)

**Nguyên tắc: fail an toàn (fail-safe).** Mất dependency làm kết quả **sai** hoặc **mất kiểm soát chi phí/bảo mật** → từ chối (503). Chỉ **giảm chất lượng/tốc độ** → degraded có kiểm soát + alert. Quan trọng nhất là **chủ động quyết định**, đừng để crash ngẫu nhiên. Production thật: chạy Redis HA (replica/sentinel/cluster) để hiếm khi rơi vào tình huống này.
